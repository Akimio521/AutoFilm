from webdav3.client import Client
import argparse,os,requests,time

# 如果depth为None，则会递归遍历整个WebDAV服务器
# 如果depth为正整数，则会递归遍历到指定深度
# 如果depth为0，则只会遍历当前文件夹中的文件和文件夹，不会继续递归遍历下一级文件夹。
def list_files(webdav_url, username, password, depth=None):
    # 创建WebDAV客户端
    options = {
        'webdav_hostname': webdav_url,
        'webdav_login': username,
        'webdav_password': password
    }

    client = Client(options)
    directory = []
    files = []
    q = 1
    while q < 15:
        try:
            # 获取WebDAV服务器上的文件列表
            items = client.list()
        except:
            print(f'第{q}次连接失败，{q+1}秒后重试...')
            q += 1
            time.sleep(q)
        else:
            if q > 1:
                print('重连成功...')
            break

    if q == 15:
        print('连接失败，请检查网络设置！')
        exit()

    for item in items[1:]:
        if item[-1] == '/':
            # 如果是文件夹，则递归遍历其中的文件和文件夹
            if depth is None or depth > 0:
                subdirectory, subfiles = list_files(webdav_url + item, username, password, depth=None if depth is None else depth - 1)
                directory += [item + subitem for subitem in subdirectory]
                files += [item + subitem for subitem in subfiles]
            else:
                directory.append(item)
        else:
            files.append(item)
    return directory, files


# 解析命令行参数
parser = argparse.ArgumentParser(description='Autofilm script')
parser.add_argument('--webdav_url', type=str, help='WebDAV服务器地址', required=True)
parser.add_argument('--username', type=str, help='WebDAV账号', required=True)
parser.add_argument('--password', type=str, help='WebDAV密码', required=True)
parser.add_argument('--output_path', type=str, help='输出文件目录', required=True)
args = parser.parse_args()

# 调用函数获取文件列表并保存到本地
directory = list_files(args.webdav_url, args.username, args.password, depth=None)[0]
files = list_files(args.webdav_url, args.username, args.password, depth=None)[1]

urls = [args.webdav_url + item for item in directory + files]

for url in urls:
    if url[-1] == '/':
        continue
    filename = os.path.basename(url)
    local_path = os.path.join(args.output_path, url.replace(args.webdav_url, '').lstrip('/'))
    if filename[-3:].upper() in ['MP4', 'MKV', 'FLV', 'AVI']:
        if not os.path.exists(os.path.join(args.output_path, filename[:-3] + 'strm')):
            print('正在处理：' + filename)
            try:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(os.path.join(local_path[:-3] + 'strm'), "w", encoding='utf-8') as f:
                    f.write(url.replace('/dav', '/d'))
            except:
                print(filename + '处理失败，文件名包含特殊符号，建议重命名！')
    elif filename[-3:].upper() in ['ASS', 'SRT', 'SSA', 'JPG', 'NFO']:
        if not os.path.exists(local_path):
            p = 1
            while p < 10:
                try:
                    print('正在下载：' + filename)
                    r = requests.get(url.replace('/dav', '/d'))
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    with open(local_path, 'wb') as f:
                        f.write(r.content)
                        f.close
                except:
                    print(f'第{p}次下载失败，{p + 1}秒后重试...')
                    p += 1
                    time.sleep(p)
                else:
                    if p > 1:
                        print('重新下载成功！')
                    break

print('处理完毕！')