#!/bi/software/Anaconda3/bin/python

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import configparser
import os 
import sys
import re

batch = sys.argv[1]
senddir = sys.argv[2]
mailconfigfile = sys.argv[3]
infoFile = sys.argv[4]

seqDate = (re.split('_',batch))[1]
ossDir = batch + "/"

for dirpath, dirnames, filenames in os.walk(os.path.abspath(senddir)):
    for filename in filenames:
        if os.path.basename(infoFile) in filename:
            continue
        file = os.path.abspath(os.path.join(dirpath, filename))
        ossdirSub = os.path.dirname(os.path.join("/biosan-bioinfo/ZhengDaFuSan/", ossDir))
        os.system(f"/bi/software/ossutil64 cp --checkpoint-dir=.ossutil_checkpoint -f {file} oss:/{ossdirSub}/ -c /bi/BioCodeHub/.ossutil/.ossutilconfig_bs")

def load_config(Mailconfigfile):
    config = configparser.ConfigParser()
    config.read(Mailconfigfile)
    return config

config = load_config(mailconfigfile)
sender = config['mail']['sender_email']
receiver = config['mail']['receiver_zdfs']
acc = config['mail']['receiver_zdfs_acc']
password = config['mail']['password']
smtpserver = config['mail']['smtp_server']

from email import encoders
msgRoot = MIMEMultipart('alternative')
msgRoot['Subject'] = 'WGS数据下载通知-郑州大学第三附属医院-' + seqDate + '批次'
msgRoot['From'] = sender
msgRoot['To'] = receiver
msgRoot['Cc'] = acc

content='您好：\n\n您送检的全基因组测序样本数据已上传到阿里云oss://biosan-bioinfo/ZhengDaFuSan/' + ossDir + '，请您及时下载！\n\n如有任何问题请及时联系我们，谢谢，祝好！\n\n注意：传输数据自今日起2周后将自动删除，所有数据释放后，请您自行做好备份工作，以免后期数据丢失造成不必要的损失。'
cont=MIMEText(content,'plain','utf-8')
msgRoot.attach(cont)


#发送附件
att = MIMEText(open(infoFile, 'rb').read(), 'base64', 'gb2312')
att["Content-Type"] = 'application/octet-stream'
att.add_header('Content-Disposition', 'attachment', filename=('gb2312', '', batch + '.sampleinfo.郑大附三.txt'))
msgRoot.attach(att)

smtp = smtplib.SMTP()
smtp.connect(smtpserver)
smtp.login(sender, password)
smtp.sendmail(sender, receiver.split(', ') + acc.split(', '), msgRoot.as_string())
smtp.quit()
