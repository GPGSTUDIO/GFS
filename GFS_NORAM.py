from Converter import *
from deep_hexlib import *
from GFS_LIB import *
import sys
import subprocess
import os

filename = sys.argv[1]
gp = "gp_.exe"
find = b"GF\x00\x01"

if filename.startswith("\\\\"):
    disk = True
else:
    disk = False

def readsector(sector,sectormax):
    with open(filename,"rb") as f:
        filesystemd = f.read(11)
        finded = filesystemd.find(find)
        if not finded == -1:
            offset = 11+517
            for i in range(sectormax):
                if i == sector:
                    return getfullneed(4096,filename,offset)
                offset += 4096+517
  
def writesector(offset, data):
    aligned_offset = (offset // 512) * 512
    offset_in_sector = offset - aligned_offset
    total_bytes = len(data)
    end_position = offset_in_sector + total_bytes
    sectors_needed = (end_position + 511) // 512 
    
    # Читаем существующие данные
    existing_data = getfullneed(sectors_needed * 512, filename, aligned_offset, disk)
    if len(existing_data) < sectors_needed * 512:
        existing_data = existing_data.ljust(sectors_needed * 512, b'\x00')
    
    # Заменяем только нужную часть
    new_data = bytearray(existing_data)
    for i in range(total_bytes):
        if offset_in_sector + i < len(new_data):
            new_data[offset_in_sector + i] = data[i]
    
    # Дополняем до кратности 512
    if len(new_data) % 512 != 0:
        new_data.extend(b'\x00' * (512 - (len(new_data) % 512)))
    
    # Записываем
    if disk:
        cmd = [gp, str(aligned_offset), filename]
        result = subprocess.run(cmd, input=bytes(new_data), capture_output=True, text=False)
        if result.returncode != 0:
            raise Exception(f"Write error: {result.stderr}")
    else:
        with open(filename, 'r+b') as f:
            f.seek(aligned_offset)
            f.write(new_data)
            
def save(filecount, filenamed, filedesc, filetype, filedata=None, delete=None):
    filename_encoded = filenamed.encode('cp1251').ljust(256, b'\x00')[:256]
    filedesc_encoded = filedesc.encode('cp1251').ljust(256, b'\x00')[:256]
    
    # Для файлов - готовим все данные, для директорий - нули
    if filetype == 0 and filedata:
        filesize = len(filedata)
        # Разбиваем на чанки по 4096 байт
        data_chunks = [filedata[i:i+4096] for i in range(0, filesize, 4096)]
        first_chunk = data_chunks[0].ljust(4096, b'\x00')[:4096]
    else:
        filesize = 0
        first_chunk = b'\x00' * 4096
        data_chunks = []

    target_index = None
    target_offset = None
    
    # Ищем существующий файл для удаления или перезаписи
    for i in range(filecount):
        offset = 11 + (i * (517 + 4096))
        metadata = getfullneed(517, filename, offset, disk)
        current_name = metadata[:256].replace(b'\x00', b'').decode('cp1251')
        current_type = metadata[512]
        
        if delete and current_name == filenamed:
            # Помечаем как удаленный (type=3) вместо затирания
            deleted_metadata = (filename_encoded + filedesc_encoded + 
                              bytes([3]) + b'\x00\x00\x00\x00')
            writesector(offset, deleted_metadata)
            return
        
        if current_type == 3 and target_index is None:
            target_index = i
            target_offset = offset

    # Если не нашли удаленный файл, создаем новый
    if target_index is None and not delete:
        target_index = filecount
        target_offset = 11 + (filecount * (517 + 4096))
        
        # Обновляем заголовок
        new_filecount = filecount + 1 + max(0, len(data_chunks) - 1)
        new_fullsize = new_filecount * (517 + 4096) + 11
        
        new_header = (b"GF\x00\x01" + 
                     new_fullsize.to_bytes(4, 'big') + 
                     bytes([88]) + 
                     new_filecount.to_bytes(2, 'big'))
        writesector(0, new_header)
    
    if target_index is None:
        print("No space found or file not found for deletion")
        return
   
    # Записываем основной файл
    filesize_bytes = filesize.to_bytes(4, 'big')
    metadata_block = (filename_encoded + filedesc_encoded + 
                     bytes([filetype]) + filesize_bytes)
    
    writesector(target_offset, metadata_block)
    writesector(target_offset + 517, first_chunk)
    
    # Записываем блоки-продолжения для оставшихся данных
    for i, chunk in enumerate(data_chunks[1:], 1):
        continuation_offset = target_offset + (i * (517 + 4096))
        
        # Создаем запись-продолжение (тип 2)
        cont_metadata = (b'\x00' * 256 +
                       f"Continuation {i}".encode('cp1251').ljust(256, b'\x00')[:256] +
                       bytes([2]) +
                       len(chunk).to_bytes(4, 'big'))
        
        padded_chunk = chunk.ljust(4096, b'\x00')[:4096]
        
        # Записываем блок-продолжение
        writesector(continuation_offset, cont_metadata)
        writesector(continuation_offset + 517, padded_chunk)
    
with open(filename,"rb") as f:
    filesystem = f.read(11)
    finded = filesystem.find(find)
    if not finded == -1:
        filecount = binary2deciminal(hex2binary(text2hex(filesystem[10:11],True)))
        offset = 11
        for i in range(filecount):
            filesystem += getfullneed(517,filename,offset)
            offset += 4096+517

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
        toskip = []
        localproblem = 0
        for i in range(filecount):
            names.append(data[:256].replace(b"\x00",b"").decode("cp1251")) # Имя
            data = data[256:]
            descs.append(data[:256].replace(b"\x00",b"").decode("cp1251")) # Описание
            data = data[256:]
            localtype = data[0]
            types.append(localtype) # Тип: 1 Папка, 0 Файл, 2 Пропуск, 3 Удалённый
            data = data[1:]
            filesizes.append(binary2deciminal(hex2binary(text2hex(data[:4],True)))) # Размер
            data = data[4:]
            if localtype==2 or localtype==3:
                toskip.append(i)
                del names[i-localproblem], descs[i-localproblem], types[i-localproblem], filesizes[i-localproblem]
                localproblem += 1
        for i in range(filecount):
            if i in toskip:
                filecount -= 1
            else:
                filestexts.append(b"")
        try:
            while True:
                inputted = input(">")
                if inputted.startswith("mkdir "):
                    inputted = inputted[6:]
                    save(filecount,inputted,"Created in shell",1)
                    names.append(inputted)
                    descs.append("Created in shell")
                    types.append(1)
                    filesizes.append(0)
                    filestexts.append(b"")
                    filecount += 1
                if inputted.startswith("rm "):
                    inputted = inputted[3:]
                    index_del = None
                    for index in range(filecount):
                        if names[index] == inputted:
                            save(filecount,inputted,"Created in shell",3,delete=True)
                            del names[index], descs[index], types[index], filesizes[index], filestexts[index]
                            filecount -= 1
                            break
                elif inputted == "ls":
                    for i in range(filecount):
                        print(f"{i+1}. {"dir" if types[i] else "file"} {filesizes[i]} bytes: {names[i]} - {descs[i]}")
                elif inputted.startswith("cat "):
                    try:
                        for index in range(filecount):
                            if names[index] == inputted[4:]:
                                cat_data = b""
                                if filestexts[index]==b"":
                                    if filesizes[index]>4096:
                                        for i in range(filesizes[index]//4096+1):
                                            cat_data += readsector(index+i,index+filesizes[index]//4096+1)
                                    else:
                                        cat_data = readsector(index,filesizes[index]//4096+1+index)
                                else:
                                    cat_data = filestexts[index]
                                print(cat_data[:filesizes[index]].decode("utf-8",errors="replace"))
                    except:
                        pass
                elif inputted.startswith("copy 1 "):
                    # copy 1 - копирование файла В файловую систему
                    try:
                        source_path = inputted[7:]  # путь к файлу на диске
                        filenamed = os.path.basename(source_path)  # имя файла
                        
                        # Читаем файл с диска
                        with open(source_path, 'rb') as f:
                            filedatad = f.read()
                        
                        # Сохраняем в файловую систему
                        save(filecount, filenamed, "Copied from disk", 0, filedatad)
                        names.append(filenamed)
                        descs.append("Copied from disk")
                        types.append(0)
                        filesizes.append(len(filedatad))
                        filestexts.append(filedatad)
                        filecount += 1
                        
                        print(f"File '{filenamed}' copied to filesystem ({len(filedatad)} bytes)")
                    except Exception as e:
                        print(f"Error copying file: {e}")
                
                elif inputted.startswith("copy 2 "):
                    # copy 2 - копирование файла ИЗ файловой системы
                    try:
                        args = inputted[7:].split()
                        if len(args) < 2:
                            print("Usage: copy 2 <filename_in_fs> <destination_path>")
                            continue
                        
                        fs_filename = args[0]  # имя файла в файловой системе
                        dest_path = args[1]    # путь для сохранения на диск
                        
                        # Ищем файл в файловой системе
                        for index in range(filecount):
                            if names[index] == fs_filename and types[index] == 0:  # 0 = файл
                                # Получаем данные файла
                                file_data = b""
                                if filestexts[index] == b"":
                                    if filesizes[index] > 4096:
                                        for i in range(filesizes[index] // 4096 + 1):
                                            file_data += readsector(index + i, index + filesizes[index] // 4096 + 1)
                                    else:
                                        file_data = readsector(index, filesizes[index] // 4096 + 1 + index)
                                else:
                                    file_data = filestexts[index]
                                
                                # Сохраняем на диск
                                with open(dest_path, 'wb') as f:
                                    f.write(file_data[:filesizes[index]])
                                
                                print(f"File '{fs_filename}' copied to '{dest_path}' ({filesizes[index]} bytes)")
                                break
                        else:
                            print(f"File '{fs_filename}' not found in filesystem")
                    except Exception as e:
                        print(f"Error copying file: {e}")
        except KeyboardInterrupt:
            print("Saving filesystem...")
else:
    print("File system not found! format with GFS_Format.py")