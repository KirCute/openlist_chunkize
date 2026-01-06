# openlist_chunkize

一个 AI 生成 + 我自己修改了一点的脚本，用于把一个本地目录变为有效的“分块”驱动。同时计算被变为分块文件的哈希值，利用分块驱动的哈希缓存性质使之在上传过程中跳过哈希计算过程。

这个脚本不会对文件执行分块，只会把它变成仅含有0号块（其内容就是文件本身）的假分块文件。

利用这个脚本，你可以将位于通过SFTP、FTP等驱动连接的远程主机上的大文件，经位于本地的 OpenList 秒传到网盘上，而不会产生本地主机与远程主机之间的流量。具体做法是先将远程主机上的文件分块化，再在本地主机上新建分块驱动，再进行分块驱动到网盘的复制。

### 用法

```bash
python chunkize.py --hashes md5 ~/target_path
python chunkize.py -a md5 sha1 sha256 --prefix "[openlist_chunk]" ~/target_path 
python chunkize.py -a md5 --num_workers 2 --skip ".*\.txt" --p "[openlist_chunk]" ~/target_path
python chunkize.py -a sha1 -n 2 -s ".*\.txt" --verbose ~/target_path
```
