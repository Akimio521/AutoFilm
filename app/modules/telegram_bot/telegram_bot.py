from typing import Dict, List, Callable, Awaitable, Any, Optional, Union, Tuple, Set, TypeVar
import asyncio
import time
from functools import partial
from datetime import datetime
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

from app.core import logger, settings
from app.utils import Singleton
from app.modules import Alist2Strm, Ani2Alist


class TelegramBot(metaclass=Singleton):
    """
    Telegram Bot for AutoFilm
    提供 Telegram 远程控制功能
    """

    def __init__(
            self,
            token: str,
            allowed_users: Optional[List[int]] = None,
            proxy_url: Optional[str] = None,
            admin_users: Optional[List[int]] = None,
            **kwargs
    ) -> None:
        """
        Initialize TelegramBot

        :param token: Telegram Bot Token
        :param allowed_users: List of allowed Telegram user IDs
        :param proxy_url: Proxy URL for Telegram API
        :param admin_users: List of admin user IDs with extra privileges
        :param kwargs: Additional arguments not used by this class
        """
        self.token = token
        self.allowed_users = allowed_users or []
        self.admin_users = admin_users or []
        self.proxy_url = proxy_url

        # 保证管理员也在允许用户列表中
        if self.admin_users:
            self.allowed_users = list(set(self.allowed_users + self.admin_users))

        # 存储正在运行的任务
        self.running_tasks: Dict[
            str, tuple[asyncio.Task, str, int, float]] = {}  # task_id: (task, task_name, user_id, start_time)

        # 存储任务历史
        self.task_history: List[Dict[str, Any]] = []  # [{task_name, status, duration, user_id, timestamp}]
        self.max_history = 50  # 最大历史记录数

        # 存储用户会话状态
        self.user_sessions: Dict[int, Dict[str, Any]] = {}  # user_id: {last_activity, current_menu, etc}

        # 创建应用
        app_kwargs = {}
        if proxy_url:
            app_kwargs["proxy_url"] = proxy_url

        self.application = Application.builder().token(token).build()

        # 添加处理程序
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        self.application.add_handler(CommandHandler("menu", self._menu_command))
        self.application.add_handler(CommandHandler("update", self._update_command))
        self.application.add_handler(CommandHandler("status", self._status_command))
        self.application.add_handler(CommandHandler("history", self._history_command))
        self.application.add_handler(CommandHandler("cancel", self._cancel_command))
        self.application.add_handler(CommandHandler("admin", self._admin_command))

        # 添加回调查询处理程序
        self.application.add_handler(CallbackQueryHandler(self._button_callback))

        # 添加错误处理程序
        self.application.add_error_handler(self._error_handler)

        # 添加通用消息处理程序
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self._text_handler
        ))

        logger.info("Telegram Bot initialized successfully")

    async def start(self) -> None:
        """
        Start the Telegram Bot
        
        启动Telegram机器人，初始化应用并开始轮询更新
        """
        logger.info("Starting Telegram Bot...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("Telegram Bot started successfully")

    async def stop(self) -> None:
        """
        Stop the Telegram Bot
        
        停止Telegram机器人，取消所有运行中的任务并关闭应用
        """
        logger.info("Stopping Telegram Bot...")

        # 取消所有运行中的任务
        for task_id, (task, task_name, _, _) in list(self.running_tasks.items()):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        logger.info("Telegram Bot stopped successfully")

    def _is_user_allowed(self, user_id: int) -> bool:
        """
        Check if user is allowed to use the bot
        
        :param user_id: Telegram用户ID
        :return: 如果用户被允许使用机器人则为True，否则为False
        """
        if not self.allowed_users:
            return True
        return user_id in self.allowed_users

    def _is_admin(self, user_id: int) -> bool:
        """
        Check if user is an admin
        
        :param user_id: Telegram用户ID
        :return: 如果用户是管理员则为True，否则为False
        """
        return user_id in self.admin_users

    def _update_session(self, user_id: int, **kwargs) -> None:
        """
        Update user session data
        
        :param user_id: Telegram用户ID
        :param kwargs: 要更新的会话数据键值对
        """
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {}

        self.user_sessions[user_id].update(
            last_activity=time.time(),
            **kwargs
        )

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /start command
        
        :param update: 从Telegram接收的更新对象
        :param context: 处理上下文
        """
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            await update.message.reply_text("🚫 您没有权限使用此机器人。")
            return

        # 更新用户会话
        self._update_session(user.id, current_menu="main")

        # 创建欢迎消息
        welcome_message = (
            f"👋 欢迎，{user.first_name}！\n\n"
            f"*AutoFilm {settings.APP_VERSION}* 远程控制中心\n\n"
            f"您可以通过此机器人远程管理 AutoFilm 系统，包括触发更新、查看任务状态等功能。\n\n"
            f"请选择以下选项或输入 /help 获取更多帮助信息。"
        )

        # 创建主菜单按钮
        keyboard = self._get_main_menu_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /help command
        
        :param update: 从Telegram接收的更新对象
        :param context: 处理上下文
        """
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            await update.message.reply_text("🚫 您没有权限使用此机器人。")
            return

        help_text = (
            "*AutoFilm 远程控制助手 - 帮助信息*\n\n"
            "可用命令：\n\n"
            "🔹 /menu - 显示主菜单\n"
            "🔹 /update - 运行更新任务\n"
            "🔹 /status - 查看正在运行的任务\n"
            "🔹 /history - 查看任务执行历史\n"
            "🔹 /cancel - 取消正在运行的任务\n"
            "🔹 /help - 显示此帮助信息\n"
            "🔹 /admin - 管理员功能（仅限管理员）\n\n"
            "您还可以通过点击菜单按钮来使用各种功能。"
        )

        keyboard = [[InlineKeyboardButton("返回主菜单", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /menu command
        
        :param update: 从Telegram接收的更新对象
        :param context: 处理上下文
        """
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            await update.message.reply_text("🚫 您没有权限使用此机器人。")
            return

        # 更新用户会话
        self._update_session(user.id, current_menu="main")

        keyboard = self._get_main_menu_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📋 *主菜单*\n\n请选择您想要执行的操作：",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    def _get_main_menu_keyboard(self) -> List[List[InlineKeyboardButton]]:
        """
        Get main menu keyboard buttons
        
        :return: 主菜单的按钮列表
        """
        keyboard = [
            [InlineKeyboardButton("🔄 更新任务", callback_data="menu_update")],
            [InlineKeyboardButton("📊 任务状态", callback_data="menu_status")],
            [InlineKeyboardButton("📝 历史记录", callback_data="menu_history")],
            [InlineKeyboardButton("❌ 取消任务", callback_data="menu_cancel")],
            [InlineKeyboardButton("❓ 帮助信息", callback_data="menu_help")],
        ]

        # 如果有管理员权限，添加管理员菜单
        if self.admin_users:
            keyboard.append([InlineKeyboardButton("⚙️ 管理选项", callback_data="menu_admin")])

        return keyboard

    async def _update_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /update command
        
        :param update: 从Telegram接收的更新对象
        :param context: 处理上下文
        """
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            await update.message.reply_text("🚫 您没有权限使用此机器人。")
            return

        # 更新用户会话
        self._update_session(user.id, current_menu="update")

        # 创建更新选项键盘
        keyboard = self._get_update_menu_keyboard()

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔄 *更新任务*\n\n请选择要更新的内容：",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    def _get_update_menu_keyboard(self) -> List[List[InlineKeyboardButton]]:
        """
        Get update menu keyboard buttons
        
        :return: 更新菜单的按钮列表
        """
        keyboard = []

        # 添加 Alist2Strm 任务
        if settings.AlistServerList:
            keyboard.append([InlineKeyboardButton("✅ 更新全部 Alist2Strm", callback_data="update_all_alist2strm")])
            for server in settings.AlistServerList:
                server_id = server.get("id", "未命名")
                keyboard.append([
                    InlineKeyboardButton(f"🎬 更新 Alist2Strm: {server_id}",
                                         callback_data=f"update_alist2strm_{server_id}")
                ])

        # 添加 Ani2Alist 任务
        if settings.Ani2AlistList:
            keyboard.append([InlineKeyboardButton("✅ 更新全部 Ani2Alist", callback_data="update_all_ani2alist")])
            for server in settings.Ani2AlistList:
                server_id = server.get("id", "未命名")
                keyboard.append([
                    InlineKeyboardButton(f"📺 更新 Ani2Alist: {server_id}",
                                         callback_data=f"update_ani2alist_{server_id}")
                ])

        # 添加所有任务
        if settings.AlistServerList and settings.Ani2AlistList:
            keyboard.append([InlineKeyboardButton("🔄 更新所有任务", callback_data="update_all")])

        # 返回主菜单按钮
        keyboard.append([InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")])

        return keyboard

    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /status command
        
        :param update: 从Telegram接收的更新对象
        :param context: 处理上下文
        """
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            await update.message.reply_text("🚫 您没有权限使用此机器人。")
            return

        # 更新用户会话
        self._update_session(user.id, current_menu="status")

        if not self.running_tasks:
            keyboard = [[InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "📊 *任务状态*\n\n当前没有正在运行的任务。",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        status_text = "📊 *任务状态*\n\n当前运行的任务：\n\n"
        now = time.time()

        for task_id, (task, task_name, user_id, start_time) in self.running_tasks.items():
            status = "🔄 运行中" if not task.done() else "✅ 已完成"
            duration = now - start_time
            duration_text = self._format_duration(duration)

            # 查找用户名
            username = "未知用户"
            for chat_id, session in self.user_sessions.items():
                if chat_id == user_id:
                    username = session.get("username", "未知用户")
                    break

            status_text += f"• *{task_name}*\n  状态: {status}\n  持续时间: {duration_text}\n  启动者: {username}\n\n"

        keyboard = [
            [InlineKeyboardButton("🔄 刷新", callback_data="refresh_status")],
            [InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            status_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /history command
        
        :param update: 从Telegram接收的更新对象
        :param context: 处理上下文
        """
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            await update.message.reply_text("🚫 您没有权限使用此机器人。")
            return

        # 更新用户会话
        self._update_session(user.id, current_menu="history")

        if not self.task_history:
            keyboard = [[InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "📝 *任务历史*\n\n没有任务执行历史记录。",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # 最多显示最近的 10 条记录
        recent_history = self.task_history[-10:]

        history_text = "📝 *任务历史记录*\n\n最近的任务：\n\n"

        for i, record in enumerate(reversed(recent_history), 1):
            task_name = record["task_name"]
            status = record["status"]
            duration = record["duration"]
            timestamp = record["timestamp"]

            # 格式化时间和持续时间
            time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            duration_text = self._format_duration(duration)

            # 状态图标
            status_icon = "✅" if status == "completed" else "❌" if status == "cancelled" else "⚠️"

            history_text += f"{i}. *{task_name}*\n  状态: {status_icon} {status}\n  持续时间: {duration_text}\n  完成时间: {time_str}\n\n"

        keyboard = [
            [InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            history_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /cancel command
        
        :param update: 从Telegram接收的更新对象
        :param context: 处理上下文
        """
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            await update.message.reply_text("🚫 您没有权限使用此机器人。")
            return

        # 更新用户会话
        self._update_session(user.id, current_menu="cancel")

        if not self.running_tasks:
            keyboard = [[InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "❌ *取消任务*\n\n当前没有正在运行的任务。",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # 创建取消选项键盘
        keyboard = []
        for task_id, (task, task_name, _, _) in self.running_tasks.items():
            if not task.done():
                keyboard.append([
                    InlineKeyboardButton(f"❌ 取消: {task_name}", callback_data=f"cancel_{task_id}")
                ])

        if keyboard:
            keyboard.append([InlineKeyboardButton("❌ 取消所有任务", callback_data="cancel_all")])
            keyboard.append([InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "❌ *取消任务*\n\n请选择要取消的任务：",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            keyboard = [[InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "❌ *取消任务*\n\n当前没有可取消的任务。",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    async def _admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /admin command (admin only)
        
        :param update: 从Telegram接收的更新对象
        :param context: 处理上下文
        """
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            await update.message.reply_text("🚫 您没有权限使用此机器人。")
            return

        if not self._is_admin(user.id):
            await update.message.reply_text("🚫 此命令仅限管理员使用。")
            return

        # 更新用户会话
        self._update_session(user.id, current_menu="admin")

        # 创建管理员菜单
        keyboard = [
            [InlineKeyboardButton("👥 查看当前用户", callback_data="admin_list_users")],
            [InlineKeyboardButton("📊 系统状态", callback_data="admin_system_status")],
            [InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚙️ *管理员控制面板*\n\n请选择操作：",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle regular text messages
        
        :param update: 从Telegram接收的更新对象
        :param context: 处理上下文
        """
        user = update.effective_user
        if not self._is_user_allowed(user.id):
            await update.message.reply_text("🚫 您没有权限使用此机器人。")
            return

        # 保存用户名
        self._update_session(
            user.id,
            username=user.username or f"{user.first_name} {user.last_name}".strip() or str(user.id)
        )

        # 检查用户会话中的当前菜单
        session = self.user_sessions.get(user.id, {})
        current_menu = session.get("current_menu", "main")

        # 如果有特定的菜单处理逻辑，可以在这里添加
        # 例如，如果用户在某个特定的菜单中，我们可以根据他们的输入执行操作

        # 如果没有特定的处理逻辑，返回主菜单
        keyboard = self._get_main_menu_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "👋 我收到了您的消息，但我主要通过命令和按钮交互。\n\n请使用菜单按钮或命令来操作：",
            reply_markup=reply_markup
        )

    async def _button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle button callbacks
        
        :param update: 从Telegram接收的更新对象
        :param context: 处理上下文
        """
        query = update.callback_query
        user = query.from_user

        if not self._is_user_allowed(user.id):
            await query.answer("🚫 您没有权限使用此功能。")
            return

        # 保存用户名
        self._update_session(
            user.id,
            username=user.username or f"{user.first_name} {user.last_name}".strip() or str(user.id)
        )

        callback_data = query.data
        await query.answer()

        # 主菜单导航
        if callback_data == "main_menu":
            # 更新用户会话
            self._update_session(user.id, current_menu="main")

            keyboard = self._get_main_menu_keyboard()
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "📋 *主菜单*\n\n请选择您想要执行的操作：",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # 菜单导航
        if callback_data.startswith("menu_"):
            menu_type = callback_data[5:]  # 去掉 "menu_" 前缀

            if menu_type == "update":
                await self._handle_menu_update(query, user.id)
            elif menu_type == "status":
                await self._handle_menu_status(query, user.id)
            elif menu_type == "history":
                await self._handle_menu_history(query, user.id)
            elif menu_type == "cancel":
                await self._handle_menu_cancel(query, user.id)
            elif menu_type == "help":
                await self._handle_menu_help(query, user.id)
            elif menu_type == "admin":
                await self._handle_menu_admin(query, user.id)
            return

        # 刷新状态
        if callback_data == "refresh_status":
            await self._handle_menu_status(query, user.id)
            return

        # 管理员功能
        if callback_data.startswith("admin_"):
            if not self._is_admin(user.id):
                await query.edit_message_text("🚫 此功能仅限管理员使用。")
                return

            admin_action = callback_data[6:]  # 去掉 "admin_" 前缀

            if admin_action == "list_users":
                await self._handle_admin_list_users(query)
            elif admin_action == "system_status":
                await self._handle_admin_system_status(query)
            return

        # 更新命令
        if callback_data == "update_all":
            await self._run_all_tasks(query, user.id)
        elif callback_data == "update_all_alist2strm":
            await self._run_all_alist2strm(query, user.id)
        elif callback_data == "update_all_ani2alist":
            await self._run_all_ani2alist(query, user.id)
        elif callback_data.startswith("update_alist2strm_"):
            server_id = callback_data[len("update_alist2strm_"):]
            await self._run_alist2strm(query, server_id, user.id)
        elif callback_data.startswith("update_ani2alist_"):
            server_id = callback_data[len("update_ani2alist_"):]
            await self._run_ani2alist(query, server_id, user.id)

        # 取消命令
        elif callback_data == "cancel_all":
            await self._cancel_all_tasks(query, user.id)
        elif callback_data.startswith("cancel_"):
            task_id = callback_data[len("cancel_"):]
            await self._cancel_task(query, task_id, user.id)

    async def _handle_menu_update(self, query: CallbackQuery, user_id: int) -> None:
        """
        Handle update menu selection
        
        :param query: Telegram回调查询对象
        :param user_id: 用户ID
        """
        # 更新用户会话
        self._update_session(user_id, current_menu="update")

        keyboard = self._get_update_menu_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "🔄 *更新任务*\n\n请选择要更新的内容：",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _handle_menu_status(self, query: CallbackQuery, user_id: int) -> None:
        """
        Handle status menu selection
        
        :param query: Telegram回调查询对象
        :param user_id: 用户ID
        """
        # 更新用户会话
        self._update_session(user_id, current_menu="status")

        if not self.running_tasks:
            keyboard = [[InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "📊 *任务状态*\n\n当前没有正在运行的任务。",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        status_text = "📊 *任务状态*\n\n当前运行的任务：\n\n"
        now = time.time()

        for task_id, (task, task_name, task_user_id, start_time) in self.running_tasks.items():
            status = "🔄 运行中" if not task.done() else "✅ 已完成"
            duration = now - start_time
            duration_text = self._format_duration(duration)

            # 查找用户名
            username = "未知用户"
            for chat_id, session in self.user_sessions.items():
                if chat_id == task_user_id:
                    username = session.get("username", "未知用户")
                    break

            status_text += f"• *{task_name}*\n  状态: {status}\n  持续时间: {duration_text}\n  启动者: {username}\n\n"

        keyboard = [
            [InlineKeyboardButton("🔄 刷新", callback_data="refresh_status")],
            [InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            status_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _handle_menu_history(self, query: CallbackQuery, user_id: int) -> None:
        """
        Handle history menu selection
        
        :param query: Telegram回调查询对象
        :param user_id: 用户ID
        """
        # 更新用户会话
        self._update_session(user_id, current_menu="history")

        if not self.task_history:
            keyboard = [[InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "📝 *任务历史*\n\n没有任务执行历史记录。",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        ## 最多显示最近的 10 条记录
        recent_history = self.task_history[-10:]

        history_text = "📝 *任务历史记录*\n\n最近的任务：\n\n"

        for i, record in enumerate(reversed(recent_history), 1):
            task_name = record["task_name"]
            status = record["status"]
            duration = record["duration"]
            timestamp = record["timestamp"]

            # 格式化时间和持续时间
            time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            duration_text = self._format_duration(duration)

            # 状态图标
            status_icon = "✅" if status == "completed" else "❌" if status == "cancelled" else "⚠️"

            history_text += f"{i}. *{task_name}*\n  状态: {status_icon} {status}\n  持续时间: {duration_text}\n  完成时间: {time_str}\n\n"

        keyboard = [
            [InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            history_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _handle_menu_cancel(self, query: CallbackQuery, user_id: int) -> None:
        """
        Handle cancel menu selection
        
        :param query: Telegram回调查询对象
        :param user_id: 用户ID
        """
        # 更新用户会话
        self._update_session(user_id, current_menu="cancel")

        if not self.running_tasks:
            keyboard = [[InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "❌ *取消任务*\n\n当前没有正在运行的任务。",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # 创建取消选项键盘
        keyboard = []
        for task_id, (task, task_name, _, _) in self.running_tasks.items():
            if not task.done():
                keyboard.append([
                    InlineKeyboardButton(f"❌ 取消: {task_name}", callback_data=f"cancel_{task_id}")
                ])

        if keyboard:
            keyboard.append([InlineKeyboardButton("❌ 取消所有任务", callback_data="cancel_all")])
            keyboard.append([InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ *取消任务*\n\n请选择要取消的任务：",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            keyboard = [[InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "❌ *取消任务*\n\n当前没有可取消的任务。",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    async def _handle_menu_help(self, query: CallbackQuery, user_id: int) -> None:
        """
        Handle help menu selection
        
        :param query: Telegram回调查询对象
        :param user_id: 用户ID
        """
        # 更新用户会话
        self._update_session(user_id, current_menu="help")

        help_text = (
            "*AutoFilm 远程控制助手 - 帮助信息*\n\n"
            "可用命令：\n\n"
            "🔹 /menu - 显示主菜单\n"
            "🔹 /update - 运行更新任务\n"
            "🔹 /status - 查看正在运行的任务\n"
            "🔹 /history - 查看任务执行历史\n"
            "🔹 /cancel - 取消正在运行的任务\n"
            "🔹 /help - 显示此帮助信息\n"
            "🔹 /admin - 管理员功能（仅限管理员）\n\n"
            "您还可以通过点击菜单按钮来使用各种功能。"
        )

        keyboard = [[InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _handle_menu_admin(self, query: CallbackQuery, user_id: int) -> None:
        """
        Handle admin menu selection
        
        :param query: Telegram回调查询对象
        :param user_id: 用户ID
        """
        if not self._is_admin(user_id):
            keyboard = [[InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "🚫 *权限错误*\n\n此菜单仅限管理员使用。",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # 更新用户会话
        self._update_session(user_id, current_menu="admin")

        # 创建管理员菜单
        keyboard = [
            [InlineKeyboardButton("👥 查看当前用户", callback_data="admin_list_users")],
            [InlineKeyboardButton("📊 系统状态", callback_data="admin_system_status")],
            [InlineKeyboardButton("⬅️ 返回主菜单", callback_data="main_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚙️ *管理员控制面板*\n\n请选择操作：",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _handle_admin_list_users(self, query: CallbackQuery) -> None:
        """
        Handle admin list users action
        
        :param query: Telegram回调查询对象
        """
        user_text = "👥 *当前活跃用户*\n\n"

        if not self.user_sessions:
            user_text += "当前没有活跃用户。"
        else:
            for user_id, session in self.user_sessions.items():
                username = session.get("username", "未知用户")
                last_activity = session.get("last_activity", 0)
                current_menu = session.get("current_menu", "未知")

                # 计算上次活动时间
                if last_activity:
                    last_seen = time.time() - last_activity
                    last_seen_text = self._format_duration(last_seen) + " 前"
                else:
                    last_seen_text = "未知"

                # 标记管理员
                admin_mark = "👑 " if self._is_admin(user_id) else ""

                user_text += f"• {admin_mark}*{username}* (ID: {user_id})\n  最后活动: {last_seen_text}\n  当前菜单: {current_menu}\n\n"

        keyboard = [[InlineKeyboardButton("⬅️ 返回管理菜单", callback_data="menu_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            user_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _handle_admin_system_status(self, query: CallbackQuery) -> None:
        """
        Handle admin system status action
        
        :param query: Telegram回调查询对象
        """
        import platform
        import psutil  # 确保已安装 psutil 库

        # 系统信息
        system_info = f"系统: {platform.system()} {platform.release()}\n"
        system_info += f"Python: {platform.python_version()}\n"

        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        system_info += f"CPU 使用率: {cpu_percent}%\n"

        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used = memory.used / (1024 * 1024 * 1024)  # 转换为 GB
        memory_total = memory.total / (1024 * 1024 * 1024)  # 转换为 GB
        system_info += f"内存使用率: {memory_percent}% ({memory_used:.2f}GB / {memory_total:.2f}GB)\n"

        # 磁盘使用率
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used = disk.used / (1024 * 1024 * 1024)  # 转换为 GB
        disk_total = disk.total / (1024 * 1024 * 1024)  # 转换为 GB
        system_info += f"磁盘使用率: {disk_percent}% ({disk_used:.2f}GB / {disk_total:.2f}GB)\n"

        # 进程信息
        process = psutil.Process()
        process_cpu = process.cpu_percent(interval=1)
        process_memory = process.memory_info().rss / (1024 * 1024)  # 转换为 MB
        system_info += f"进程 CPU 使用率: {process_cpu}%\n"
        system_info += f"进程内存使用: {process_memory:.2f}MB\n"

        # 运行时间
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time
        uptime_text = self._format_duration(uptime)
        system_info += f"系统运行时间: {uptime_text}\n"

        # AutoFilm 信息
        system_info += f"\nAutoFilm 版本: {settings.APP_VERSION}\n"
        system_info += f"运行任务数: {len(self.running_tasks)}\n"
        system_info += f"历史任务数: {len(self.task_history)}\n"
        system_info += f"活跃用户数: {len(self.user_sessions)}\n"

        keyboard = [[InlineKeyboardButton("⬅️ 返回管理菜单", callback_data="menu_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"📊 *系统状态*\n\n{system_info}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _run_task(
        self,
        callback_query: CallbackQuery,
        task_func: Callable[..., Awaitable[Any]],
        task_args: Dict[str, Any],
        task_name: str,
        user_id: int
    ) -> None:
        """
        Run a task and manage its lifecycle
        
        :param callback_query: Telegram回调查询对象
        :param task_func: 要运行的异步函数
        :param task_args: 函数的参数字典
        :param task_name: 任务的描述性名称
        :param user_id: 发起任务的用户ID
        """
        # 创建唯一任务 ID
        task_id = f"{task_name}_{id(task_func)}"

        # 检查是否有类似任务正在运行
        for existing_id, (existing_task, existing_name, _, _) in self.running_tasks.items():
            if existing_name == task_name and not existing_task.done():
                await callback_query.edit_message_text(
                    f"⚠️ *任务已在运行*\n\n任务 {task_name} 已经在运行中。",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

        # 创建消息
        await callback_query.edit_message_text(
            f"🔄 *启动任务*\n\n正在启动任务: {task_name}...",
            parse_mode=ParseMode.MARKDOWN
        )

        start_time = time.time()

        # 创建并启动任务
        async def wrapped_task() -> None:
            try:
                await callback_query.edit_message_text(
                    f"🔄 *任务运行中*\n\n任务 {task_name} 正在运行...\n\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    parse_mode=ParseMode.MARKDOWN
                )
                await task_func(**task_args)

                # 计算任务持续时间
                end_time = time.time()
                duration = end_time - start_time
                duration_text = self._format_duration(duration)

                # 添加到历史记录
                self.task_history.append({
                    "task_name": task_name,
                    "status": "completed",
                    "duration": duration,
                    "user_id": user_id,
                    "timestamp": end_time
                })

                # 保持历史记录在限制范围内
                if len(self.task_history) > self.max_history:
                    self.task_history = self.task_history[-self.max_history:]

                await callback_query.edit_message_text(
                    f"✅ *任务完成*\n\n任务 {task_name} 已成功完成！\n\n耗时: {duration_text}\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    parse_mode=ParseMode.MARKDOWN
                )

            except asyncio.CancelledError:
                # 计算任务持续时间
                end_time = time.time()
                duration = end_time - start_time

                # 添加到历史记录
                self.task_history.append({
                    "task_name": task_name,
                    "status": "cancelled",
                    "duration": duration,
                    "user_id": user_id,
                    "timestamp": end_time
                })

                await callback_query.edit_message_text(
                    f"❌ *任务已取消*\n\n任务 {task_name} 已被用户取消。",
                    parse_mode=ParseMode.MARKDOWN
                )
                raise

            except Exception as e:
                # 计算任务持续时间
                end_time = time.time()
                duration = end_time - start_time

                # 添加到历史记录
                self.task_history.append({
                    "task_name": task_name,
                    "status": "error",
                    "duration": duration,
                    "user_id": user_id,
                    "timestamp": end_time
                })

                error_msg = str(e)
                logger.error(f"任务 {task_name} 运行出错: {error_msg}")
                await callback_query.edit_message_text(
                    f"⚠️ *任务运行出错*\n\n任务 {task_name} 运行时发生错误:\n\n```\n{error_msg}\n```",
                    parse_mode=ParseMode.MARKDOWN
                )

            finally:
                # 任务完成后从运行任务中删除
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

        task = asyncio.create_task(wrapped_task())
        self.running_tasks[task_id] = (task, task_name, user_id, start_time)

    async def _run_alist2strm(self, callback_query: CallbackQuery, server_id: str, user_id: int) -> None:
        """
        Run a specific Alist2Strm task
        
        :param callback_query: Telegram回调查询对象
        :param server_id: Alist2Strm服务器的ID
        :param user_id: 发起任务的用户ID
        """
        for server in settings.AlistServerList:
            if server.get("id") == server_id:
                task_func = Alist2Strm(**server).run
                await self._run_task(
                    callback_query=callback_query,
                    task_func=task_func,
                    task_args={},
                    task_name=f"Alist2Strm: {server_id}",
                    user_id=user_id
                )
                return

        await callback_query.edit_message_text(
            f"⚠️ *配置错误*\n\n未找到ID为 {server_id} 的 Alist2Strm 配置。",
            parse_mode=ParseMode.MARKDOWN
        )

    async def _run_ani2alist(self, callback_query: CallbackQuery, server_id: str, user_id: int) -> None:
        """
        Run a specific Ani2Alist task
        
        :param callback_query: Telegram回调查询对象
        :param server_id: Ani2Alist服务器的ID
        :param user_id: 发起任务的用户ID
        """
        for server in settings.Ani2AlistList:
            if server.get("id") == server_id:
                task_func = Ani2Alist(**server).run
                await self._run_task(
                    callback_query=callback_query,
                    task_func=task_func,
                    task_args={},
                    task_name=f"Ani2Alist: {server_id}",
                    user_id=user_id
                )
                return

        await callback_query.edit_message_text(
            f"⚠️ *配置错误*\n\n未找到ID为 {server_id} 的 Ani2Alist 配置。",
            parse_mode=ParseMode.MARKDOWN
        )

    async def _run_all_alist2strm(self, callback_query: CallbackQuery, user_id: int) -> None:
        """
        Run all Alist2Strm tasks
        
        :param callback_query: Telegram回调查询对象
        :param user_id: 发起任务的用户ID
        """
        if not settings.AlistServerList:
            await callback_query.edit_message_text(
                "⚠️ *配置错误*\n\n没有配置 Alist2Strm 任务。",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        await callback_query.edit_message_text(
            "🔄 *启动任务*\n\n正在启动所有 Alist2Strm 任务...",
            parse_mode=ParseMode.MARKDOWN
        )

        async def run_all_alist2strm() -> None:
            for server in settings.AlistServerList:
                server_id = server.get("id", "未命名")
                try:
                    logger.info(f"开始执行 Alist2Strm {server_id} 任务")
                    await Alist2Strm(**server).run()
                    logger.info(f"Alist2Strm {server_id} 任务完成")
                except Exception as e:
                    logger.error(f"Alist2Strm {server_id} 任务出错: {str(e)}")
                    # 继续执行其他任务，而不是直接失败

        await self._run_task(
            callback_query=callback_query,
            task_func=run_all_alist2strm,
            task_args={},
            task_name="所有 Alist2Strm 任务",
            user_id=user_id
        )

    async def _run_all_ani2alist(self, callback_query: CallbackQuery, user_id: int) -> None:
        """
        Run all Ani2Alist tasks
        
        :param callback_query: Telegram回调查询对象
        :param user_id: 发起任务的用户ID
        """
        if not settings.Ani2AlistList:
            await callback_query.edit_message_text(
                "⚠️ *配置错误*\n\n没有配置 Ani2Alist 任务。",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        await callback_query.edit_message_text(
            "🔄 *启动任务*\n\n正在启动所有 Ani2Alist 任务...",
            parse_mode=ParseMode.MARKDOWN
        )

        async def run_all_ani2alist() -> None:
            for server in settings.Ani2AlistList:
                server_id = server.get("id", "未命名")
                try:
                    logger.info(f"开始执行 Ani2Alist {server_id} 任务")
                    await Ani2Alist(**server).run()
                    logger.info(f"Ani2Alist {server_id} 任务完成")
                except Exception as e:
                    logger.error(f"Ani2Alist {server_id} 任务出错: {str(e)}")
                    # 继续执行其他任务，而不是直接失败

        await self._run_task(
            callback_query=callback_query,
            task_func=run_all_ani2alist,
            task_args={},
            task_name="所有 Ani2Alist 任务",
            user_id=user_id
        )

    async def _run_all_tasks(self, callback_query: CallbackQuery, user_id: int) -> None:
        """
        Run all tasks (Alist2Strm and Ani2Alist)
        
        :param callback_query: Telegram回调查询对象
        :param user_id: 发起任务的用户ID
        """
        if not settings.AlistServerList and not settings.Ani2AlistList:
            await callback_query.edit_message_text(
                "⚠️ *配置错误*\n\n没有配置任何任务。",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        await callback_query.edit_message_text(
            "🔄 *启动任务*\n\n正在启动所有任务...",
            parse_mode=ParseMode.MARKDOWN
        )

        async def run_all_tasks() -> None:
            # 运行 Alist2Strm 任务
            for server in settings.AlistServerList:
                server_id = server.get("id", "未命名")
                try:
                    logger.info(f"开始执行 Alist2Strm {server_id} 任务")
                    await Alist2Strm(**server).run()
                    logger.info(f"Alist2Strm {server_id} 任务完成")
                except Exception as e:
                    logger.error(f"Alist2Strm {server_id} 任务出错: {str(e)}")
                    # 继续执行其他任务，而不是直接失败

            # 运行 Ani2Alist 任务
            for server in settings.Ani2AlistList:
                server_id = server.get("id", "未命名")
                try:
                    logger.info(f"开始执行 Ani2Alist {server_id} 任务")
                    await Ani2Alist(**server).run()
                    logger.info(f"Ani2Alist {server_id} 任务完成")
                except Exception as e:
                    logger.error(f"Ani2Alist {server_id} 任务出错: {str(e)}")
                    # 继续执行其他任务，而不是直接失败

        await self._run_task(
            callback_query=callback_query,
            task_func=run_all_tasks,
            task_args={},
            task_name="所有任务",
            user_id=user_id
        )

    async def _cancel_task(self, callback_query: CallbackQuery, task_id: str, user_id: int) -> None:
        """
        Cancel a specific task
        
        :param callback_query: Telegram回调查询对象
        :param task_id: 要取消的任务ID
        :param user_id: 发起取消的用户ID
        """
        if task_id not in self.running_tasks:
            await callback_query.edit_message_text(
                "⚠️ *任务不存在*\n\n指定的任务不存在或已完成。",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        task, task_name, task_user_id, _ = self.running_tasks[task_id]

        # 检查是否管理员或任务发起人
        is_owner = user_id == task_user_id
        is_admin = self._is_admin(user_id)

        if not is_owner and not is_admin:
            await callback_query.edit_message_text(
                "🚫 *权限错误*\n\n您无权取消此任务。只有任务发起人或管理员可以取消任务。",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        if task.done():
            await callback_query.edit_message_text(
                f"ℹ️ *任务已完成*\n\n任务 {task_name} 已完成，无需取消。",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # 取消任务
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # 添加取消操作者信息
        canceller = "管理员" if is_admin and not is_owner else "发起人"

        await callback_query.edit_message_text(
            f"❌ *任务已取消*\n\n任务 {task_name} 已被{canceller}取消。",
            parse_mode=ParseMode.MARKDOWN
        )

    async def _cancel_all_tasks(self, callback_query: CallbackQuery, user_id: int) -> None:
        """
        Cancel all running tasks
        
        :param callback_query: Telegram回调查询对象
        :param user_id: 发起取消的用户ID
        """
        if not self.running_tasks:
            await callback_query.edit_message_text(
                "ℹ️ *没有任务*\n\n当前没有正在运行的任务。",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # 检查是否为管理员
        is_admin = self._is_admin(user_id)

        # 获取用户可以取消的任务
        can_cancel_tasks = []
        for task_id, (task, task_name, task_user_id, _) in list(self.running_tasks.items()):
            if not task.done() and (is_admin or task_user_id == user_id):
                can_cancel_tasks.append((task_id, task, task_name))

        if not can_cancel_tasks:
            await callback_query.edit_message_text(
                "🚫 *权限错误*\n\n您没有权限取消当前运行的任何任务。",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # 取消所有可以取消的任务
        cancelled_count = 0
        for task_id, task, task_name in can_cancel_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            cancelled_count += 1

        # 根据是否是管理员提供不同的消息
        if is_admin:
            message = f"❌ *任务已取消*\n\n管理员已取消 {cancelled_count} 个任务。"
        else:
            message = f"❌ *任务已取消*\n\n您已取消 {cancelled_count} 个任务。"

        await callback_query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Log errors caused by updates.
        
        :param update: 从Telegram接收的更新对象
        :param context: 处理上下文，包含错误信息
        """
        logger.error(f"Telegram Bot error: {context.error}")

        # 如果是回调查询，通知用户
        if isinstance(update, Update) and update.callback_query:
            await update.callback_query.answer("发生错误，请稍后重试。")

            try:
                await update.callback_query.edit_message_text(
                    f"⚠️ *操作出错*\n\n执行操作时发生错误，请稍后重试。\n\n错误详情: {str(context.error)}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass

    def _format_duration(self, seconds: float) -> str:
        """
        Format a duration in seconds to a human-readable string
        
        :param seconds: 秒数
        :return: 格式化后的人类可读时间字符串
        """
        if seconds < 60:
            return f"{seconds:.1f} 秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} 分钟"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.1f} 小时"
        else:
            days = seconds / 86400
            return f"{days:.1f} 天"

    async def run(self) -> None:
        """
        Run the Telegram bot (keeps running until explicitly stopped)
        
        运行Telegram机器人，直到被明确停止
        """
        try:
            await self.start()
            # Keep the bot running
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            await self.stop()
