#!/bi/software/Anaconda3/bin/python

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import configparser
import os 
import re
import argparse

parser = argparse.ArgumentParser(description='WGS山大生殖数据上传和邮件通知脚本')
parser.add_argument('-b', '--batch', help='批次号')
parser.add_argument('-i', '--senddir', help='要上传的目录')
parser.add_argument('-c', '--mailconfigfile', help='邮件配置文件路径')
parser.add_argument('-s','--sampleinfoFile', help='样本信息表路径')
parser.add_argument('-t','--test', action='store_true', help='测试模式，上传到test目录')

args = parser.parse_args()
batch = args.batch
senddir = args.senddir
mailconfigfile = args.mailconfigfile
infoFile = args.sampleinfoFile
test = args.test

batch_parts = re.split('_', batch)
seqDate = batch_parts[1]
ossDir = f'{batch_parts[0]}_{batch_parts[1]}_data'

for dirpath, dirnames, filenames in os.walk(os.path.abspath(senddir)):
    for filename in filenames:
        if os.path.basename(infoFile) in filename:
            continue
        file = os.path.abspath(os.path.join(dirpath, filename))
        ossdirSub =  os.path.join("/biosan-delivery/test/", ossDir) if test else os.path.join("/biosan-delivery/BeiJingJinYu/", ossDir)
        # 计算当前文件所在目录相对于根目录的路径
        rel_dir = os.path.relpath(dirpath, senddir)
        if rel_dir == '.':
            # 文件就在根目录下，不需要额外子目录
            oss_subdir = ossdirSub
        else:
            oss_subdir = os.path.join(ossdirSub, rel_dir)
        #print(f"/bi/software/obsutil_linux_amd64_5.4.11/obsutil cp -f -link {file} obs:/{oss_subdir}/{filename} -config=/bi/BioCodeHub/WGS/obs.config")
        #print(f"/bi/software/obsutil_linux_amd64_5.4.11/obsutil ls obs:/{ossdirSub}/  -config=/bi/BioCodeHub/WGS/obs.config")
        os.system(f"/bi/software/obsutil_linux_amd64_5.4.11/obsutil cp -f -link {file} obs:/{oss_subdir}/{filename} -config=/bi/BioCodeHub/WGS/obs.config")

def load_config(Mailconfigfile):
    config = configparser.ConfigParser()
    config.read(Mailconfigfile)
    return config

config = load_config(mailconfigfile)
sender = config['mail']['sender_email']
receiver = config['mail']['receiver_bkw']
acc = config['mail']['receiver_bkw_acc']
password = config['mail']['password']
smtpserver = config['mail']['smtp_server']

from email import encoders
msgRoot = MIMEMultipart('alternative')
msgRoot['Subject'] = 'WGS数据下载通知-北京金域医学检验实验室有限公司-' + seqDate + '批次'
msgRoot['From'] = sender
msgRoot['To'] = receiver

content='您好：\n\n您送检的全基因组测序样本数据已上传到华为云obs:/' + ossdirSub + '，请您及时下载！\n\n如有任何问题请及时联系我们，谢谢，祝好！\n\n注意：传输数据自今日起2周后将自动删除，所有数据释放后，请您自行做好备份工作，以免后期数据丢失造成不必要的损失。'
cont=MIMEText(content,'plain','utf-8')
msgRoot.attach(cont)


#发送附件
att = MIMEText(open(infoFile, 'rb').read(), 'base64', 'gb2312')
att["Content-Type"] = 'application/octet-stream'
att.add_header('Content-Disposition', 'attachment', filename=('gb2312', '', ossDir + '.sampleinfo.tsv'))
msgRoot.attach(att)

smtp = smtplib.SMTP()
smtp.connect(smtpserver)
smtp.login(sender, password)
smtp.sendmail(sender, receiver.split(',') + (acc.split(', ') if acc else []), msgRoot.as_string())
smtp.quit()
