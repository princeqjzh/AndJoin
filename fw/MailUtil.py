#! /usr/bin/python
# serverInfo['name'], serverInfo['user'], serverInfo['passwd']
# python 2.3.*: email.Utils email.Encoders

from __future__ import with_statement

# from email import MIMEMultipart, MIMEBase
from email.utils import COMMASPACE, formatdate
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEBase import MIMEBase
from os import path
# Apr 25: use the customized smtplib module
# sys.path.insert(0, '/usr/share/jython/Lib')
from smtplib import SMTP as SMTP


# from ssmtplib import SMTP_SSL as SMTP


def send_mail(serverInfo, fro, to, subject, text, attachments):
    assert type(serverInfo) == dict
    assert type(to) == list
    assert type(attachments) == list
    if 'office365' in serverInfo['name']:
        send_mail_office365(serverInfo, fro, to, subject, text, attachments)
    else:
        send_mail_exchange(serverInfo, fro, to, subject, text, attachments)


def send_mail_exchange(serverInfo, fro, to, subject, text, attachments):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = fro
        msg['To'] = COMMASPACE.join(to)  # COMMASPACE==', ' used to display recipents in mail
        msg['Date'] = formatdate(localtime=True)
        print '[send_mail] attaching text...'
        html_att = MIMEText(text, 'html', 'utf-8')
        #        att = MIMEText(attachments, 'plain', 'utf-8')
        msg.attach(html_att)
        #        msg.attach(attachments)
        for item in attachments:
            part = MIMEBase('application', 'octet-stream')  # 'octet-stream': binary data
            # print '[send_mail] before set payload'
            part.set_payload(open(item, 'rb').read())
            encoders.encode_base64(part)
            print '[send_mail] attaching file %s' % path.basename(item)
            part.add_header('Content-Disposition', 'attachment; filename="%s"' % path.basename(item))
            msg.attach(part)
        print '[send_mail] initializing smtp server...'
        smtpserver = SMTP(serverInfo['name'], 25)
        print '[sendmail] set debuglevel...'
        smtpserver.set_debuglevel(False)
        print '[send_mail] sending...'
        # conn=smtpserver.connect(serverInfo['name'],25)
        smtpserver.sendmail(msg['From'], [msg['To']], msg.as_string())

    except Exception, e:
        # you will catch a exception if tls is required
        print "[send_mail] initializing mail failed; %s" % str(e)  # give a error message
        raise Exception(str(e))


def send_mail_office365(serverInfo, fro, to, subject, text, attachments):

    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = fro
        msg['To'] = COMMASPACE.join(to)  # COMMASPACE==', ' used to display recipents in mail
        msg['Date'] = formatdate(localtime=True)
        print '[send_mail] attaching text...'
        html_att = MIMEText(text, 'html', 'utf-8')
        #        att = MIMEText(attachments, 'plain', 'utf-8')
        msg.attach(html_att)
        #        msg.attach(attachments)
        for item in attachments:
            part = MIMEBase('application', 'octet-stream')  # 'octet-stream': binary data
            # print '[send_mail] before set payload'
            part.set_payload(open(item, 'rb').read())
            encoders.encode_base64(part)
            print '[send_mail] attaching file %s' % path.basename(item)
            part.add_header('Content-Disposition', 'attachment; filename="%s"' % path.basename(item))
            msg.attach(part)
        print '[send_mail] initializing smtp server...'
        smtpserver = SMTP(serverInfo['name'], 587)  # port changed to 587 after switched to office365
    except Exception, e:
        # you will catch a exception if tls is required
        print "[send_mail] initializing mail failed; %s" % str(e)  # give a error message
        raise Exception(str(e))

    try:
        # If TLS is used
        print '[send_mail] ehlo1...'
        smtpserver.ehlo()
        print '[send_mail] start tls...'
        smtpserver.starttls()
        print '[send_mail] ehlo2...'
        smtpserver.ehlo()
        print '[send_mail] logging in via tls...'
        smtpserver.login(serverInfo['user'], serverInfo['password'])
        print '[send_mail] logged in, sending...'
        smtpserver.sendmail(msg['From'], [msg['To']], msg.as_string())
        print '[send_mail] Email sent'
        smtpserver.quit()  # bye bye
    except Exception:
        # if tls is set for non-tls servers you would have raised an exception, so....
        smtpserver.ehlo()
        print '[send_mail] logging in via non-tls ...'
        smtpserver.login(serverInfo['user'], serverInfo['password'])
        print '[send_mail] logged in, sending...'
        smtpserver.sendmail(msg['From'], [msg['To']], msg.as_string())
        print '[send_mail] Email sent'
        smtpserver.quit()  # bye bye
