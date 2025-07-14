from io import BytesIO
from base64 import b64encode

import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from sklearn.cluster import KMeans  # type: ignore


class PhotoUtils:
    @staticmethod
    def get_primary_color(
        img: Image.Image, num_colors: int = 5, bg_clusters: int = 1
    ) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        """
        从PIL图像对象中提取主题色（背景色）和适配的文字颜色
        :param img: PIL图像对象
        :param num_colors: 要提取的主色数量（默认5）
        :param bg_clusters: 用于合并背景色的主色数量（默认1）
        :return: 返回一个元组，包含背景色和文字颜色
        格式为 ((r, g, b), (r, g, b))
        其中背景色是RGB格式，文字颜色是根据背景色亮度计算的
        """
        # 将PIL图像转换为NumPy数组 (RGB格式)
        img_array = np.array(img)

        # 如果图像有透明通道，移除alpha通道
        if img_array.shape[2] == 4:
            img_array = img_array[:, :, :3]

        # 将图像数据重塑为2D数组 (像素 x RGB)
        pixel_data = img_array.reshape((-1, 3))

        # 使用K-Means聚类提取主色
        kmeans = KMeans(n_clusters=num_colors, n_init=10, random_state=42)
        kmeans.fit(pixel_data)

        # 获取聚类中心和对应的像素数量
        colors = kmeans.cluster_centers_
        counts = np.bincount(kmeans.labels_)

        # 按出现频率排序颜色
        sorted_indices = np.argsort(counts)[::-1]
        main_colors = colors[sorted_indices].astype(int)

        # 合并指定数量的聚类作为背景色
        background_color = np.mean(main_colors[:bg_clusters], axis=0).astype(int)

        # 计算背景色的相对亮度
        r, g, b = background_color
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

        # 根据亮度选择文字颜色
        text_color = (0, 0, 0) if luminance > 0.5 else (255, 255, 255)

        return tuple(background_color), tuple(text_color)

    @staticmethod
    def create_gradient_background(
        width: int,
        height: int,
        color: tuple[int, int, int],
    ) -> Image.Image:
        """
        创建一个从左到右的渐变背景，使用遮罩技术实现渐变效果
        左侧颜色更深，右侧颜色适中，提供更明显的渐变效果
        :param width: 背景宽度
        :param height: 背景高度
        :param color: 主题色，格式为 (r, g, b)
        :return: 渐变背景图像
        """
        base = Image.new("RGB", (width, height), color)  # 创建基础图像（右侧原始颜色）

        # 创建渐变遮罩（水平方向：左黑右白）
        gradient = Image.new("L", (width, 1))  # 单行渐变
        gradient_data = []
        for x in range(width):
            # 计算渐变值：左侧0（全黑），右侧255（全白）
            value = int(255 * x / max(1, width - 1))
            gradient_data.append(value)

        # 应用渐变数据并垂直拉伸
        gradient.putdata(gradient_data)
        mask = gradient.resize((width, height))

        # 创建暗色版本（左侧颜色）
        dark_factor = 0.5  # 颜色加深系数
        dark_color = (
            int(color[0] * dark_factor),
            int(color[1] * dark_factor),
            int(color[2] * dark_factor),
        )
        dark = Image.new("RGB", (width, height), dark_color)

        # 使用遮罩混合两种颜色
        return Image.composite(base, dark, mask)

    @staticmethod
    def add_shadow(
        img: Image.Image, offset=(5, 5), shadow_color=(0, 0, 0, 100), blur_radius=3
    ) -> Image.Image:
        """
        给图片添加右侧和底部阴影
        :param img: 原始图片（PIL.Image对象）
        :param offset: 阴影偏移量，(x, y)格式
        :param shadow_color: 阴影颜色，RGBA格式
        :param blur_radius: 阴影模糊半径
        :return: 添加了阴影的新图片
        """
        # 创建一个透明背景，比原图大一些，以容纳阴影
        shadow_width = img.width + offset[0] + blur_radius * 2
        shadow_height = img.height + offset[1] + blur_radius * 2

        shadow = Image.new("RGBA", (shadow_width, shadow_height), (0, 0, 0, 0))
        shadow_layer = Image.new("RGBA", img.size, shadow_color)  # 创建阴影层

        # 将阴影层粘贴到偏移位置
        shadow.paste(shadow_layer, (blur_radius + offset[0], blur_radius + offset[1]))
        # 模糊阴影
        shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))
        # 创建结果图像
        result = Image.new("RGBA", shadow.size, (0, 0, 0, 0))
        # 将原图粘贴到结果图像上
        result.paste(
            img, (blur_radius, blur_radius), img if img.mode == "RGBA" else None
        )
        # 合并阴影和原图（保持原图在上层）
        return Image.alpha_composite(shadow, result)

    @staticmethod
    def apply_rounded_corners(image: Image.Image, radius: int) -> Image.Image:
        """应用圆角效果"""
        mask = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), image.size], radius=radius, fill=255)
        result = Image.new("RGBA", image.size, (0, 0, 0, 0))
        result.paste(image, (0, 0), mask)
        return result

    @staticmethod
    def draw_text_on_image(
        image: Image.Image,
        text: str,
        position: tuple[int, int],
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        fill_color: tuple[int, int, int] = (255, 255, 255),
        shadow_enabled: bool = False,
        shadow_color: tuple[int, int, int, int] = (0, 0, 0, 180),
        shadow_offset: tuple[int, int] = (2, 2),
    ) -> None:
        """
        在图像上绘制文字，可选添加文字阴影
        :param image: PIL.Image对象
        :param text: 要绘制的文字
        :param position: 文字位置 (x, y)
        :param font: 字体对象
        :param font_size: 字体大小
        :param fill_color: 文字颜色，RGB格式
        :param shadow_enabled: 是否启用文字阴影
        :param shadow_color: 阴影颜色，RGBA格式
        :param shadow_offset: 阴影偏移量，(x, y)格式
        :return: 添加了文字的图像
        """
        draw = ImageDraw.Draw(image)
        # 如果启用阴影，先绘制阴影文字
        if shadow_enabled:
            shadow_position = (
                position[0] + shadow_offset[0],
                position[1] + shadow_offset[1],
            )
            draw.text(shadow_position, text, font=font, fill=shadow_color)
        # 绘制正常文字
        draw.text(position, text, font=font, fill=fill_color)

    @staticmethod
    def draw_multiline_text_on_image(
        image: Image.Image,
        texts: list[str],
        position: tuple[int, int],
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        font_size: int,
        line_spacing: int = 10,
        fill_color=(255, 255, 255),
        shadow_enabled=False,
        shadow_color=(0, 0, 0, 180),
        shadow_offset=(2, 2),
    ):
        """
        在图像上绘制多行文字，根据空格自动换行，可选添加文字阴影

        :param image: PIL.Image对象
        :param text: 要绘制的文字
        :param position: 第一行文字位置 (x, y)
        :param font: 字体对象
        :param font_size: 字体大小
        :param line_spacing: 行间距
        :param fill_color: 文字颜色，RGBA格式
        :param shadow_enabled: 是否启用文字阴影
        :param shadow_color: 阴影颜色，RGB格式
        :param shadow_offset: 阴影偏移量，(x, y)格式
        """
        draw = ImageDraw.Draw(image)
        x, y = position
        for i, line in enumerate(texts):
            current_y = y + i * (font_size + line_spacing)
            if shadow_enabled:  # 如果启用阴影，先绘制阴影文字
                shadow_x = x + shadow_offset[0]
                shadow_y = current_y + shadow_offset[1]
                draw.text((shadow_x, shadow_y), line, font=font, fill=shadow_color)
            draw.text((x, current_y), line, font=font, fill=fill_color)  # 绘制正常文字

    @staticmethod
    def encode_image(image: Image.Image, format: str = "PNG") -> bytes:
        """
        将PIL图像编码为base64字节数据（用于API上传）
        :param image: PIL图像对象
        :param format: 图像格式，默认为PNG
        :return: 图像的base64编码字节数据
        """
        buffer = BytesIO()
        if image.mode in ("RGBA", "LA"):  # 确保图像是RGB格式（移除透明通道）
            background = Image.new("RGB", image.size, (255, 255, 255))  # 创建白色背景
            if image.mode == "RGBA":
                background.paste(image, mask=image.split()[-1])  # 使用alpha通道作为mask
            else:
                background.paste(image)
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

        image.save(buffer, format=format)
        buffer.seek(0)
        return b64encode(buffer.getvalue())  # 返回base64编码的字节数据
