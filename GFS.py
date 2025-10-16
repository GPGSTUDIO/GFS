from Converter import *
from deep_hexlib import *
import subprocess
import sys

Modified = False
updated = True

from GFS_LIB import *

def getfull(toread,filename_to_open):
    with open(filename_to_open,"rb") as f:
        filesystem = f.read(toread)
       
    find = b"GF\x00\x00"

    finded = filesystem.find(find)

    if not finded == -1:
        data = filesystem
        data = data[finded+len(find):] # Обрезаем мусор в начале
        size = data[:4] # 4 Байта под размер файла это до 4 гигабайт
        data = data[4:] # Обрезаем эти 4 байта
        partition = data[0] # 1 Байт под указатель раздела
        data = data[1:] # Обрезаем байт и сразу проверяем его
        data = data[:binary2deciminal(hex2binary(text2hex(size,True)))] # Обрезаем мусор в конце
        if partition == 88:
            filecount = data[:2] # Проверяем количество файлов
            data = data[2:]
            filecount = binary2deciminal(hex2binary(text2hex(filecount,True)))
            names = []
            descs = []
            types = []
            filesizes = []
            filestexts = []
            for i in range(filecount):
                names.append(data[:256].replace(b"\x00",b"").decode("cp1251")) # Имя
                data = data[256:]
                descs.append(data[:256].replace(b"\x00",b"").decode("cp1251")) # Описание
                data = data[256:]
                types.append(data[0]) # Тип: 1 Папка, 0 Файл
                data = data[1:]
                filesizes.append(binary2deciminal(hex2binary(text2hex(data[:4],True)))) # Размер
                data = data[4:]
            for i in range(filecount):
                if types[i] == 0:
                    filestexts.append(data[:filesizes[i]])
                    data = data[filesizes[i]:]
                else:
                    filestexts.append(b"")
            return filestexts

filename_to_open = sys.argv[1]
toread = 0

if filename_to_open.startswith("\\\\"):
    disk = True
else:
    disk = False
   
with open(filename_to_open,"rb") as f:
    filesystem = f.read(11)
    sumetry = 256+256+1+4
    filestexts = []
    if filesystem[8] == 88:
        filecount = binary2deciminal(hex2binary(text2hex(filesystem[10:11],True)))
        filecountd = filecount * sumetry
        runcount = filecountd+11
        filesystem += f.read(filecountd)
        temp_filesystem = filesystem[11:]
        temp_filesystem = temp_filesystem[:filecountd]
        for i in range(filecount):
            temp_filesystem = temp_filesystem[513:]
            runcount += binary2deciminal(hex2binary(text2hex(temp_filesystem[:4],True)))
            temp_filesystem = temp_filesystem[4:]
        toread = runcount
        
   
find = b"GF\x00\x00"

finded = filesystem.find(find)

if not finded == -1:
    data = filesystem
    data = data[finded+len(find):] # Обрезаем мусор в начале
    size = data[:4] # 4 Байта под размер файла это до 4 гигабайт
    data = data[4:] # Обрезаем эти 4 байта
    partition = data[0] # 1 Байт под указатель раздела
    data = data[1:] # Обрезаем байт и сразу проверяем его
    data = data[:binary2deciminal(hex2binary(text2hex(size,True)))] # Обрезаем мусор в конце
    if partition == 88:
        filecount = data[:2] # Проверяем количество файлов
        data = data[2:]
        filecount = binary2deciminal(hex2binary(text2hex(filecount,True)))
        names = []
        descs = []
        types = []
        filesizes = []
        filestexts = []
        for i in range(filecount):
            names.append(data[:256].replace(b"\x00",b"").decode("cp1251")) # Имя
            data = data[256:]
            descs.append(data[:256].replace(b"\x00",b"").decode("cp1251")) # Описание
            data = data[256:]
            types.append(data[0]) # Тип: 1 Папка, 0 Файл
            data = data[1:]
            filesizes.append(binary2deciminal(hex2binary(text2hex(data[:4],True)))) # Размер
            data = data[4:]
        for i in range(filecount):
            if types[i] == 0:
                filestexts.append(data[:filesizes[i]])
                data = data[filesizes[i]:]
            else:
                filestexts.append(b"")
        try:
            while True:
                inputed = input(filename_to_open+">")
                if inputed == "ls":
                    for i in range(filecount):
                        if types[i] == 1:
                            curty = "dir"
                        elif types[i] == 0:
                            curty = "file"
                        else:
                            curty = "unknown"
                        print(f"{i+1}: {curty}, {filesizes[i]} bytes. {names[i]} - {descs[i]}")
                elif inputed.startswith("cat "):
                    for index in range(filecount):
                        if names[index] == inputed[4:]:
                            if filestexts[index]==b"":
                                offset = 11
                                offset += filecount * 517
                                for i in range(index):
                                    offset += filesizes[i]
                                    data = getfullneed(filesizes[index], filename_to_open, offset)
                                    filestexts[index] = data
                            print(filestexts[index].decode("utf-8",errors="replace"))
                elif inputed.startswith("mkdir "):
                    dirname = inputed[6:]
                    types.append(1)
                    names.append(dirname)
                    descs.append("Created in shell")  
                    filesizes.append(0)
                    filestexts.append(b"") 
                    filecount += 1
                    Modified = True
                elif inputed.startswith("rm "):
                    if updated:
                        filestexts = getfull(toread,filename_to_open)
                        updated = False
                    target = inputed[3:]
                    for i in range(filecount):
                        if names[i] == target:
                            del types[i], names[i], descs[i], filestexts[i], filesizes[i]
                            filecount -= 1
                            break
                elif inputed.startswith("copy "):
                    parts = inputed.split(" ", 3)
                    if len(parts) >= 4:
                        mode = parts[1]
                        
                        if mode == "1":
                            src_path = parts[2]
                            dest_name = parts[3]
                            
                            try:
                                with open(src_path, 'rb') as f:
                                    file_data = f.read()
                                
                                file_size = len(file_data)
                                dest_name = dest_name[:256]
                                
                                if dest_name in names:
                                    print(f"File {dest_name} already exists")
                                else:
                                    if updated:
                                        filestexts = getfull(toread,filename_to_open)
                                        updated = False
                                    types.append(0)
                                    names.append(dest_name)
                                    descs.append("Copied from disk")
                                    filesizes.append(file_size)
                                    filestexts.append(file_data)
                                    filecount += 1
                                    print(f"File {dest_name} copied ({file_size} bytes)")
                                    
                            except FileNotFoundError:
                                print(f"File {src_path} not found")
                            except Exception as e:
                                print(f"Copy error: {e}")
                                
                        elif mode == "2":
                            fs_name = parts[2]
                            dest_path = parts[3]
                            
                            if fs_name in names:
                                index = names.index(fs_name)
                                if types[index] == 0:
                                    try:
                                        if filestexts[index]==b"":
                                            offset = 11
                                            offset += filecount * 517
                                            for i in range(index):
                                                offset += filesizes[i]
                                            data = getfullneed(filesizes[index], filename_to_open, offset)
                                            filestexts[index] = data
                                        with open(dest_path, 'wb') as f:
                                            f.write(filestexts[index])
                                        print(f"File {fs_name} extracted to {dest_path}")
                                    except Exception as e:
                                        print(f"Extract error: {e}")
                                else:
                                    print(f"{fs_name} is not a file")
                            else:
                                print(f"File {fs_name} not found")
                                
                        else:
                            print("Usage: copy 1 <external_file> <fs_name> OR copy 2 <fs_name> <external_file>")
                    else:
                        print("Usage: copy 1 <external_file> <fs_name> OR copy 2 <fs_name> <external_file>")
        except KeyboardInterrupt:
            if updated:
                filestexts = getfull(toread,filename_to_open)
                updated = False
            print("Saving filesystem...")
            fullsize = len(types)+len(names)*256+len(descs)*256+len(filesizes)*4+2
            for i in filestexts:
                fullsize += len(i)
            files_bin = b""
            for i in range(filecount):
                files_bin += names[i].encode("cp1251").ljust(256, b'\x00')+descs[i].encode("cp1251").ljust(256, b'\x00')+bytes([types[i]])+hex2text(binary2hex(deciminal2binary(filesizes[i])).zfill(8),True,True)
            datad = find+hex2text(binary2hex(deciminal2binary(fullsize)).zfill(8),True,True)+b"X"+hex2text(binary2hex(deciminal2binary(filecount)).zfill(4),True,True)+files_bin+b"".join(filestexts)
            if disk:
                padding_size = (512 - (len(datad) % 512)) % 512
                datad += b'\x00' * padding_size
                subprocess.Popen(['gp.exe',sys.argv[1]],stdin=subprocess.PIPE).stdin.write(datad)
            else:
                with open(filename_to_open,"wb") as f:
                    f.write(datad)
else:
    print("File system not found! format with GFS_Format.py")