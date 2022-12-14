#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# изменения
# добавлен таймаут 1 час при отсутствии жр
# удаление архива в случае битого - работает 
# v3 сортировка
# v4 убрал из загрузки события транзакции
# v5 добавил логирование в файл 
# уменьшил длину комментария до 256 символов, было 50
# изменил имя индекса на indexname_ 
# ивеличил длину коментария до 400 символов
# добавил мониторинг в zabbix
# добавил таймаут 
# убрал _type в записи добавления

import glob
import json
import datetime
import string
import io
import os
import zipfile
import ftplib
import re
import time
import logging
import sys
import requests
import socket
from logging.handlers import TimedRotatingFileHandler
from elasticsearch import Elasticsearch, helpers


# отправка данных в zabbix
def zabbixmonitor(flag):
    try: 
        parametr = {'server':fullhostname, 'key':'loadjr1c', 'value':flag}
        requests.post('http://server address', params=parametr)
    except:
	    logger.error('Ошибка отправки в zabbix')

def readObject(f):

    stroka = f.readline()
    if stroka == '':
        return None
    else:
        stroka = stroka.rstrip('\n')

    isParsing = True
    result = stroka

    quotes = 0
    brackets = 0
    start_index = 0
    index = 0
    fields = []
    while isParsing:
        for ch in stroka:
            if ch == '"':
                if quotes == 0:
                    quotes += 1
                else:
                    quotes -= 1
            if quotes == 0:
                if ch == '{':
                    brackets += 1
                    if brackets == 1:
                        start_index = index + 1
                if ch == '}':
                    brackets -= 1
                    if brackets == 0:
                        fields.append(result[start_index:index])
                        isParsing = False
                        break
                if ch == ',':
                    if brackets == 1:
                        fields.append(result[start_index:index])
                        start_index = index + 1
            index += 1

        if isParsing:
            stroka = f.readline().rstrip('\n')
            # встречаются стоки с нечитаемыми символами и , в конце. в данном случае не обрабатываем это. и строка обычно длинная
            #if len(stroka) > 200:
            #    printstr = ''.join([x if x in string.printable else '' for x in stroka])
            #    if printstr.strip() == ',':
            #        return None
            result += stroka
    
    return fields


def transform_date(date1c):
    return date1c[0:4]+'-'+date1c[4:6]+'-'+date1c[6:8]+'T'+date1c[8:10]+':'+date1c[10:12]+':'+date1c[12:14] + '+07:00'
    # остается проблема часового пояса, данные в Kibana отображаются со временем +7 к выгруженному
    # omv проверил время совпадает


def parse_journal(filename, indexname):
    f = open(filename, 'r', encoding = 'utf-8-sig',  errors='ignore')
    # Проверяем файл со счетчиком
    # то считаем значение его и закроем
    CountBulk = 0
    CountBulkStr = ''
    if len(glob.glob(filename+'count')) > 0:
        f_count = open(filename+'count','r')
        CountBulkStr = (f_count.read())
        f_count.close()
    else:
        CountBulkStr = '' 
    # что бы запись вести переоткрываем в режиме записи
    f_count = open(filename+'count','w')
    # если он есть, но пустой, ну мало ли
    if len(CountBulkStr) == 0:
        CountBulk = 0
    else:
        CountBulk = int(CountBulkStr)    
    # запишем начальнео значение, так как файл сейчас уже очищен
    f_count.write(str(CountBulk))

    v = f.readline().rstrip('\n')
    f.readline()
    if v != '1CV8LOG(ver 2.0)':
        return

    counter = 0
    records = []
    print("indexname_" + indexname)
    obj = readObject(f)
    while obj is not None:
        
        counter += 1
        if counter < CountBulk:
            obj = readObject(f)
            #print("next")
            continue
        # отсеим события из списка events_remove
        event = events.get(obj[7], "")
        #print("event = " + event)
        if event in events_remove:
            #print("read next")
            obj = readObject(f)
            #if counter > 197725:
                #print("events_remove")
                #print(obj)
                #print(obj is not None)
            continue 
        application = apps.get(obj[5], "")
        mpobj = {"_index": "indexname_" + indexname,
                #"_type": "_doc", # убрал 20210928, ушло предупреждение deprication type, появилось новое
                "date": transform_date(obj[0]),
                "transaction_status": transaction_status[obj[1]],
                "transaction": obj[2],
                "user": users.get(obj[3], "<Не определен>"),
                "computer": comps.get(obj[4], ""),
                "application": russian_apps.get(application, application),
                "connection": obj[6],
                "event": russian_events.get(event, event),
                "importance": importance.get(obj[8], ''),
                "comment": delete_quotes(obj[9])[:400], # обрезаем комментарий
                "metadata": metadata.get(obj[10], ""),
                "data": delete_quotes(obj[11]),
                "presentation": delete_quotes(obj[12]),
                "server": servers.get(obj[13], ""),
                "base_port": base_ports.get(obj[14], ""),
                "ext_port": ext_ports.get(obj[15], ""),
                "session": obj[16]
                }
        
        records.append(mpobj)
        obj = readObject(f)
        #counter += 1
        print(counter)
        if counter % 1000 == 0 and CountBulk < counter:
            #print("insert data")
            helpers.bulk(el, records)
            #logger.info("1 done insert data")
            records = []
            f_count.seek(0)
            f_count.write(str(counter))
            f_count.flush

    if counter != 0:
        helpers.bulk(el, records)
        #logger.info("2 done insert data")
        records = []
    f_count.close()
    f.close()
    try:
        os.remove(filename)
        os.remove(filename+'count')
    except:
        logger.error('Ошибка удаления файла ' + filename)

def delete_quotes(s):
    if s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    else:
        return s


users = {}
comps = {}
apps = {}
events = {}
metadata = {}
servers = {}
base_ports = {}
ext_ports = {}
transaction_status = {'N': "Отсутствует", 'U': "Зафиксирована", 'R': "Не завершена", 'C': "Отменена"}
# события которые не загружаем
events_remove = ['_$Transaction$_.Begin', '_$Transaction$_.Commit', '_$Transaction$_.Rollback']

#более полный перечень событий описан на странице http://forum-1c.ru/index.php?topic=48873.0
russian_events = {'_$Session$_.Start': 'Сеанс. Начало',
                  '_$Job$_.Start':     'Фоновое задание. Запуск',
                  '_$Job$_.Succeed':   'Фоновое задание. Успешное завершение',
                  '_$Session$_.Finish': 'Сеанс. Завершение',
                  '_$Session$_.AuthenticationError': 'Сеанс. Ошибка аутентификации',
                  '_$Data$_.Update': 'Данные. Изменение',
                  '_$Transaction$_.Begin': 'Транзакция. Начало',
                  '_$Transaction$_.Commit': 'Транзакция. Фиксация',
                  '_$Transaction$_.Rollback': 'Транзакция. Откат',
                  '_$Session$_.Authentication': 'Сеанс. Аутентификация',
                  '_$Data$_.New': 'Данные. Добавление',
                  '_$Data$_.Post': 'Данные. Проведение',
                  '_$PerformError$_': 'Ошибка выполнения',
                  '_$Job$_.Fail': 'Фоновое задание. Ошибка выполнения',
                  '_$Data$_.Unpost': 'Данные. Отмена проведения',
                  '_$Data$_.Delete': 'Данные. Удаление',
                  '_$Access$_.AccessDenied': 'Доступ. Отказ в доступе',
                  '_$User$_.Update': 'Пользователи. Изменение',
                  '_$User$_.New': 'Пользователи. Добавление',
                  '_$InfoBase$_.ConfigUpdate': 'Информационная база. Изменение конфигурации',
                  '_$InfoBase$_.DBConfigUpdate': 'Информационная база. Изменение конфигурации базы данных',
                  '_$Data$_.TotalsMaxPeriodUpdate': 'Данные. Изменение максимального периода рассчитанных итогов'}

russian_apps = {'BackgroundJob': 'Фоновое задание',
                'SrvrConsole': 'Консоль кластера',
                'Designer': 'Конфигуратор ',
                '1CV8C': 'Тонкий клиент',
                '1CV8': 'Толстый клиент',
                'COMConnection': 'COM-соединение ',
                'JobScheduler': 'Планировщик заданий',
                'WebClient': 'Веб-клиент ',
                'COMConsole': 'COM-администратор '}

importance = {'I': 'Информация',
              'E': 'Ошибка',
              'W': 'Предупреждение',
              'N': 'Примечание'}

#if len(sys.argv)>0:
#    directory = sys.argv[1]
#else:
directory = "/elk-storage/1c_jr/" #ну а чо такого?
#directory = "D:\\path\\Python\\ELK1CLog\\" #для отладки на моей машине
#s директория с архивами ЖР
#directory = "D:\\elk\\"
# имя текущего хоста
fullhostname = socket.getfqdn()

level = logging.INFO
logfile = '/var/log/loadjr1c/log_loadjr1c'
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger("loadjr")
logger.setLevel(level)
formatter = logging.Formatter(FORMAT)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(level)
ch.setFormatter(formatter)
logger.addHandler(ch)
file_handler =TimedRotatingFileHandler(logfile, when='midnight') # logging.FileHandler(logfile)
file_handler.setLevel(level)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info("Директория для загруки " + directory)

while True == True: # Пока надо работать
    archs = glob.glob(directory + "*.zip")
    for zipfilename in archs:
        try:
            zip = zipfile.ZipFile(zipfilename, 'r')
        except:
            # удалять только битый 
            os.remove(zipfilename)
            logger.warning('Ошибка открытия файла ' + zipfilename)
            continue

        indexname = os.path.basename(zip.filename)[:-6]
        logger.info("Обрабатываем журнал " + zip.filename)

        dirLog = zip.filename[:-4]+'//'
        dirL = glob.glob(directory + dirLog)
        fileL = glob.glob(dirLog+"1Cv8.lgf")

        if len(dirL) == 0 or len(fileL) == 0:
            zip.extractall(zip.filename[:-4])
            # если каталог уже есть, то будем читать данные, которые в нем остались
            # в нем могли быть несколько файлов логов и первые уже были загружены, тогда не повторим их загрузку

        fileLog = io.open(dirLog+"1Cv8.lgf", 'r', encoding='utf-8-sig')
        versionLog = fileLog.readline().rstrip()
       
        if versionLog == "1CV8LOG(ver 2.0)":
            logger.info("Версия журнала регистрации 8.2")
        else:
            logger.error(u"Не корректная версия журнала регистрации." +  zip.filename)
            continue

        GUID = fileLog.readline().rstrip('\n')

        obj = readObject(fileLog)
      
        while obj is not None:
            if obj[0] == "1":
                users[obj[-1]] = delete_quotes(obj[-2])
            elif obj[0] == "2":
                comps[obj[-1]] = delete_quotes(obj[-2])
            elif obj[0] == "3":
                apps[obj[-1]] = delete_quotes(obj[-2])
            elif obj[0] == "4":
                events[obj[-1]] = delete_quotes(obj[-2])
            elif obj[0] == "5":
                metadata[obj[-1]] = delete_quotes(obj[-2])
            elif obj[0] == "6":
                servers[obj[-1]] = delete_quotes(obj[-2])
            elif obj[0] == "7":
                base_ports[obj[-1]] = obj[-2]
            elif obj[0] == "8":
                ext_ports[obj[-1]] = obj[-2]
            else:
                pass
         
            obj = readObject(fileLog)

        # использование логина пароля пока отключено, но если включить то будут эти
        # el = Elasticsearch(["http://elastic:changeme@srv-name"])
        # el = Elasticsearch(["http://elastic:changeme@srv-name-02"]) # использование логина пароля пока отключено, но если включить то будут эти
        # el = Elasticsearch(["http://elastic:changeme@srv-name-03"]) # использование логина пароля пока отключено, но если включить то будут эти
        el = Elasticsearch(["http://localhost"]) # использование логина пароля пока отключено, но если включить то будут эти

        journal = glob.glob(dirLog + "*.lgp")

        allright = True

        for filename in journal:
            logger.info("Загружаем журнал регистрации " + filename)
            try:
                parse_journal(filename, indexname.lower())
                logger.info("Загрузили журнал регистрации " + filename)
                zabbixmonitor(1) # успешная загрузка
            except:
                logger.error('Ошибка загрузки журнала регистрации: ' + filename)
                allright = False
                zabbixmonitor(0) # не успешная загрузка
                continue
        
        fileLog.close()
        zip.close()
        if allright:
            try:
                os.remove(fileLog.name)
                os.rmdir(zip.filename[:-4])
                os.remove(zipfilename)
            except:
                logger.error('Ошибка удаления файлов от архива ' + zip.filename[:-4])
    
    ftp = ftplib.FTP('ftp-temp')
    ftp.login('login', 'password')
    ftp.cwd('1c_jr_elk')
    # считаем в порядке уменьшения даты
    filenames = ftp.nlst("-t")
    pattern01 = r".*_202\d\d\d\d\d.zip$"  # надо успеть исправить до 2030
    c = 0
    # отсортируем в хронологическом порядке
    filenames.reverse()
    
    countfiles = 0
    for filename in filenames:
        if re.match(pattern01, filename):
            host_file = os.path.join(directory, filename)
            try:
                with open(host_file, 'wb') as local_file:
                    ftp.retrbinary('RETR ' + filename, local_file.write)
                    ftp.delete(filename)
                countfiles += 1
            except ftplib.error_perm:
                pass
    
            if c >= 9:
                break
            c += 1
    
    ftp.quit()
    # если нет файлов для загрузки ждем час
    if countfiles == 0:
        # если при загрузке последнего пакета ошибка, то это сообщение будет в туже секунду
        # zabbix не различает такое, поэтому делаем задержку.
        time.sleep(5) 
        zabbixmonitor(1) # скрипт работает 
        logger.info("Нет данных для загрузки, ждем 1 час")
        time.sleep(60*60)
