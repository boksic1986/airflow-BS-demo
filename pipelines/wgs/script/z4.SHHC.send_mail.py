#!/bi/software/Anaconda3/bin/python

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import configparser
import os 
import sys
import re
import pandas as pd

batch = sys.argv[1]
batchdir = sys.argv[2]
senddir = sys.argv[3]
mailconfigfile = sys.argv[4]
infoFile = sys.argv[5]
seqDate = (re.split('_',batch))[1]

def load_config(Mailconfigfile):
    config = configparser.ConfigParser()
    config.read(Mailconfigfile)
    return config

config = load_config(mailconfigfile)
sender = config['mail']['sender_email']
receiver = config['mail']['receiver_shhc']
acc = config['mail']['receiver_shhc_acc']
password = config['mail']['password']
smtpserver = config['mail']['smtp_server']

df = pd.read_csv(infoFile, sep="\t", dtype=str, encoding="utf-8")
hospitalList = list(set(df['送检医院'].tolist()))
hospitalListStr = "/".join(hospitalList)
samplelist = []
for index, row in df.iterrows():
    familyKey = f"{row['家系编号']}_{row['数据编号']}"
    familyKey = familyKey.replace('-WGS','')
    samplelist.append(familyKey)
    samplelist.append(row['数据编号'])
samplelistset = list(set(samplelist))
print(samplelistset)
df_SHHC_file = infoFile.replace('.txt','.xlsx')
df.to_excel(df_SHHC_file, engine="openpyxl", index=False)
for root, dirs, files in os.walk(batchdir):
    for file in files:
        file_path = os.path.join(root, file)
        keep = any(key in file for key in samplelistset)
        if not keep:
            os.remove(file_path)
            print(f"已删除：{file_path}")
if len(samplelistset)>0:
    os.makedirs(senddir, exist_ok=True)
    os.system(f"cp {batchdir}/* {senddir}")
    
    from email import encoders
    msgRoot = MIMEMultipart('alternative')
    msgRoot['Subject'] = 'WGS数据释放通知-' + hospitalListStr + '-' + seqDate + '批次'
    msgRoot['From'] = sender
    msgRoot['To'] = receiver
    msgRoot['Cc'] = acc
    
    content='您好：\n\n您好，' + hospitalListStr + '送检的全基因组测序样本数据已上传到域中:' + senddir + '，请您注意及时使用！\n\n如有任何问题请及时联系我们，谢谢，祝好！'
    cont=MIMEText(content,'plain','utf-8')
    msgRoot.attach(cont)
    
    
    #发送附件
    att = MIMEText(open(df_SHHC_file, 'rb').read(), 'base64', 'gb2312')
    att["Content-Type"] = 'application/octet-stream'
    att.add_header('Content-Disposition', 'attachment', filename=('gb2312', '', batch + '.sampleinfo.xlsx'))
    msgRoot.attach(att)

    smtp = smtplib.SMTP()
    smtp.connect(smtpserver)
    smtp.login(sender, password)
    smtp.sendmail(sender, receiver.split(', ') + acc.split(', '), msgRoot.as_string())
    smtp.quit()
