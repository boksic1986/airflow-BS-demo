#!/bi/software/Anaconda3/bin/python

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import configparser
import os
import sys
import pandas as pd
batch = sys.argv[1]
senddir = sys.argv[2]
mailconfigfile = sys.argv[3]
infoFile = sys.argv[4]

workdir = os.getcwd()
senddir = os.path.join(workdir, senddir)
files = os.listdir(senddir)
batch_split = '_'.join(batch.split('_')[:2])
data = batch_split.replace('WGS_', '')

def load_config(Mailconfigfile):
    config = configparser.ConfigParser()
    config.read(Mailconfigfile)
    return config

config = load_config(mailconfigfile)
sender = config['mail']['sender_email']
receiver = config['mail']['receiver_bjxh']
acc = config['mail']['receiver_bjxh_acc']
password = config['mail']['password']
smtpserver = config['mail']['smtp_server']
fail = config['mail']['receiver_bjxh_fail']

def send_email(subject, body, to_email, cc_email=None, attachment_path=None):
    msgRoot = MIMEMultipart('alternative')
    msgRoot['Subject'] = subject
    msgRoot['From'] = sender
    msgRoot['To'] = to_email
    msgRoot['Cc'] = cc_email

    content = MIMEText(body, 'plain', 'utf-8')
    msgRoot.attach(content)

    if attachment_path:
        with open(attachment_path, 'rb') as attachment_file:
            att = MIMEText(attachment_file.read(), 'base64', 'gb2312')
            att["Content-Type"] = 'application/octet-stream'
            att.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
            msgRoot.attach(att)

    smtp = smtplib.SMTP()
    smtp.connect(smtpserver)
    smtp.login(sender, password)
    smtp.sendmail(sender, to_email.split(', ') + (cc_email.split(', ') if cc_email else []), msgRoot.as_string())
    smtp.quit()

file_types = [".R1.fq.gz", ".R2.fq.gz", ".R1.fq.gz.md5", ".R2.fq.gz.md5"]
infoPath = os.path.join(workdir, infoFile)
if os.path.exists(infoPath):
    df = pd.read_csv(infoPath, sep='\t')
    for file in df['数据编号']:
        for file_suffix in file_types:
            file_name = file + file_suffix
            cmd1 = f'/bi/software/obsutil_linux_amd64_5.4.11/obsutil cp -f -link {senddir}/{file_name} obs://obs-ek-client-pumch/pumch/upload/biosan/Clinical/{batch_split}_fastq/{file_name}'
            if os.system(cmd1) != 0:
                print(f'{cmd1}，文件传输失败，中断程序')
                subject = f"WGS数据下载通知-中国医学科学院北京协和医院-{data}批次-回传失败"
                body = f"数据传输失败，文件: {file}，批次: {batch_split}"
                send_email(subject, body, fail)
                sys.exit(1)

subject = f"WGS数据下载通知-中国医学科学院北京协和医院-{data}批次"
body = f"您好：\n\n您送检的全基因组测序样本原始数据已上传到华为云obs://obs-ek-client-pumch/pumch/upload/biosan/Clinical/{batch_split}_fastq/，请您及时下载！\n\n如有任何问题请及时联系我们，谢谢，祝好！\n\n注意：所有数据释放后，请您自行做好备份工作，以免后期数据丢失造成不必要的损失。"
send_email(subject, body, receiver, acc, infoPath)