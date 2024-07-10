""""
Alist 地址树结构转换工具
"""

def structure_to_dict(text:str) -> dict:
    """
    将能够被 Alist 地址树识别的文本转换为字典

    :param text: Alist 地址树原始文本
    :return: 字典
    """
    def parse_lines(lines: list[str], start_index:int=0, indent_level:int=0):
        """
        :param lines: 文本列表
        :param start_index: 缩进空格数
        :param indent_level: 缩进级别
        """
        result_dict = {}
        i = start_index
        while i < len(lines):
            line = lines[i]
            current_indent = len(line) - len(line.lstrip())
            if current_indent > indent_level:
                # 当前行是子目录的一部分
                sub_dict, new_index = parse_lines(lines, i, current_indent)
                result_dict[current_folder] = sub_dict
                i = new_index
                continue
            elif current_indent < indent_level:
                # 当前行属于上一级目录
                break
            # 处理当前行
            parts = line.strip().split(':')
            key, value = parts[0], ':'.join(parts[1:]).strip()
            if value:
                result_dict[key] = value
            else:
                current_folder = key
                result_dict[current_folder] = {}
            i += 1
        return result_dict, i

    lines = text.strip().split('\n')
    result_dict, _ = parse_lines(lines)
    return result_dict

def dict_to_structure(dictionary:dict, indent:int = 0) -> str:
    """
    将字典转换为 能够被 Alist 地址树识别的文本

    :param dictionary: 字典
    :param indent: 缩进空格数
    :return: 能够被 Alist 地址树识别的文本
    """
    result_str = ""
    for key, value in dictionary.items():
        if isinstance(value, dict):
            result_str += " " * indent + f"{key}:\n"
            result_str += dict_to_structure(value, indent + 2)
        elif isinstance(value, str):
            result_str += " " * indent + f"{key}:{value}\n"
        else:
           raise ValueError(f"Value of {key} is not a string or dict")
        
    if indent == 0 and result_str.startswith(":"):
        result_str = result_str.lstrip(" ")
            
    return result_str
