import argparse,configparser,os

def read_config_file(config_file_path):
    """
    读取配置文件，返回一个字典
    """
    config = configparser.ConfigParser()
    config.read(config_file_path, encoding='utf-8')

    default_params = config['Default']
    default_webdav_url = default_params.get('webdav_url')
    default_username = default_params.get('username')
    default_password = default_params.get('password')
    default_output_path = default_params.get('output_path')

    params = []
    for section_name in config.sections():
        if section_name == 'Default':
            continue
        section_params = config[section_name]
        webdav_url = section_params.get('webdav_url', default_webdav_url)
        username = section_params.get('username', default_username)
        password = section_params.get('password', default_password)
        output_path = section_params.get('output_path', default_output_path)
        subtitle = section_params.getboolean('subtitle', fallback=False)
        nfo = section_params.getboolean('nfo', fallback=False)
        img = section_params.getboolean('img', fallback=False)
        params.append({
            'webdav_url': webdav_url,
            'username': username,
            'password': password,
            'output_path': output_path,
            'subtitle': subtitle,
            'nfo': nfo,
            'img': img
        })
    return params

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', required=True, help='config文件的地址')
    args = parser.parse_args()

    config_file_path = args.path
    if not os.path.isfile(config_file_path):
        print(f'找不到配置文件 {config_file_path}')
        return

    params_list = read_config_file(config_file_path)
    for params in params_list:
        command = 'python autofilm.py'
        for key, value in params.items():
            if key == 'subtitle' or key == 'nfo' or key == 'img':
                if value:
                    command += f' --{key}'
            else:
                command += f' --{key} "{value}"'
        os.system(command)

if __name__ == '__main__':
    main()
