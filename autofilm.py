from webdav3.client import Client
import os,time,requests

def list_files(webdav_url, username, password):
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
            q += 1
            print('连接失败，1秒后重试...')
            time.sleep(1)
        else:
            if q > 1:
                print('重连成功...')
            break

    for item in items[1:]:
        if item[-1] == '/':
            directory.append(item)
        else:
            files.append(item)
    return directory, files


# 输入WebDAV地址、用户名和密码
webdav_url = 'https://alist.example.com:5244/dav/' # webdav地址
username = 'your_username' # webdav用户名
password = 'your_password' # webdav密码
output_path = 'D:\\alist-for-test\\' # 输出路径

# 调用函数获取文件列表并保存到本地

directory = list_files(webdav_url, username, password)[0]
files = list_files(webdav_url, username, password)[1]

url_1 = [webdav_url]
url_2 = []
url_3 = []
files_1 = [webdav_url + str(k) for k in files]
files_2 = []
files_3 = []
if directory != []:
    for u in directory:
        url_2.append(webdav_url + u)
        files_2 += [webdav_url + u + str(i) for i in list_files(webdav_url + u, username, password)[1]]
    for x in url_2:
        l_x = list_files(x, username, password)[0]
        if l_x != []:
            for y in l_x:
                url_3.append(x + y)
                files_3 += [x + y + str(j) for j in list_files(x + y, username, password)[1]]
url = url_1 + url_2 + url_3
files_all = files_1 + files_2 + files_3

for b in files_all:
    if b[-3:].upper() in ['MP4','MKV','FLV','AVI']:
        if not os.path.exists(output_path + b.replace(webdav_url,'')[:-3] + 'strm' ):
            print('正在处理：' + b.replace(webdav_url,''))
            try:
                os.makedirs(os.path.dirname(output_path + b.replace(webdav_url,'')[:-3] + 'strm'), exist_ok=True)
                with open(output_path + b.replace(webdav_url,'')[:-3] + 'strm', "w", encoding='utf-8') as f:
                    f.write(b.replace('/dav','/d'))
            except:
                try:
                    os.makedirs(os.path.dirname(output_path + b.replace(webdav_url,'').replace('：','.')[:-3] + 'strm'), exist_ok=True)
                    with open(output_path + b.replace(webdav_url,'').replace('：','.')[:-3] + 'strm', "w", encoding='utf-8') as f:
                        f.write(b.replace('/dav','/d'))
                except:
                    print(b.replace(webdav_url,'') + '处理失败，文件名包含特殊符号，建议重命名！')
    elif b[-3:].upper() in ['ASS','SRT','SSA','JPG','NFO']:
        if not os.path.exists(output_path + b.replace(webdav_url,'')):
            p = 1
            while p < 10:
                try:
                    print('正在下载：' + output_path + b.replace(webdav_url,''))
                    r = requests.get(b.replace('/dav','/d'))
                    os.makedirs(os.path.dirname(output_path + b.replace(webdav_url,'')), exist_ok=True)
                    with open (output_path + b.replace(webdav_url,''), 'wb') as f:
                        f.write(r.content)
                        f.close
                except:
                    p += 1
                    print('下载失败，1秒后重试...')
                    time.sleep(1)
                else:
                    if p > 1:
                        print('重新下载成功！')
                    break

print('处理完毕！')
input('按任意键退出...')
