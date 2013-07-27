'''
Send a text notification to your phone when new emails are received
using Gmail.
'''
import time
import imaplib
import smtplib
from email.utils import parsedate
from email.header import decode_header
from email import message_from_string
from email.mime.text import MIMEText



class Notifier(object):
    def __init__(self, email, password, notifyEmail, settingsDict):
        self.notifyEmail = notifyEmail
        self.settings = settingsDict
        self.login(email, password)
        self.setUIDs()

    def login(self, email, password):
        M = imaplib.IMAP4_SSL('imap.gmail.com', '993')
        try:
            M.login(email, password)
            M.select()      # select inbox
            self.loginCred = (email, password)
            self.M = M
        except Exception as e:
            print "Unable to login:", e

    def getUIDs(self):
        result, data = self.M.uid('search', None, 'ALL')
        if result == 'OK':
            return data[0].split()
        else:
            print "Bad response getting UIDs"

    def setUIDs(self):
        '''gets UIDs for currently selected folder and saves them'''
        self.UIDs = self.getUIDs()

    def genEmails(self):
        '''raw email generator for inbox'''
        for uid in self.UIDs:
            result, data = self.M.uid('fetch', uid, '(RFC822)')
            yield data[0][1]

    def formatDate(self, string):
        '''returns the date/time email received into current time
        returns (date, time), date=m/dd, time=hh:mm AM/PM'''
        t = time.mktime(parsedate(string.split('\n')[1].strip()))
        tStr = time.strftime("%m/%d %I:%M %p", time.localtime(t))
        if int(tStr[:2]) < 10:
            tStr = tStr[1:]     # remove the 0 from month
        tSplit = tStr.split()
        return tSplit[0], ' '.join(tSplit[1:])

    def decodeSubject(self, string):
        '''decodes subject to ascii, removing non-ascii characters'''
        subject, encoding = decode_header(string)[0]
        if encoding == None:
            return subject
        return subject.decode(encoding).encode('ascii', 'ignore')

    def getEmailInfo(self):
        emailData = []          # (from, date, time, subject)
        for emRaw in self.genEmails():
            em = message_from_string(emRaw)
            date, time = self.formatDate(em['Received'])
            subject = self.decodeSubject(em['Subject'])
            emailData.append((em['From'], date, time, subject))
        return emailData

    def createNotification(self, incName=False, incDate=False, subjectLen=35):
        text = ''
        for address, date, time, subject in self.getEmailInfo():
            tmpText = []
            if not incName:                 # remove name from address
                if address.find('<') != -1:
                    address = address[address.index('<') + 1:][:-1]
            tmpText.append(address)
            if len(subject) > subjectLen:   # shorten subject if too long
                subject = subject[:subjectLen - 2] + '...'
            tmpText.append(subject)
            if incDate:             # include date of email in notification
                tmpText.append(date)
            text += ' '.join(tmpText + [time]) + '\n'
        return text[:-1]            # remove the very last '\n'

    def sendNotification(self):
        if not self.UIDs:
            return
        self.sendEmail(self.createNotification())
        if self.settings['de']:
            self.deleteEmails()
        if self.settings['dn']:
            self.deleteNotification()

    def sendEmail(self, content):
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.starttls()
        server.login(self.loginCred[0], self.loginCred[1])
        msg = MIMEText(content)
        msg['From'] = self.loginCred[0]
        msg['To'] = self.notifyEmail
        msg['Subject'] = 'Generated Notification'
        server.sendmail(self.loginCred[0], self.notifyEmail, msg.as_string())
        server.quit()

    def deleteEmails(self):
        for uid in self.UIDs:
            self.M.uid('store', uid, '+FLAGS', '\\Deleted')
        self.M.expunge()

    def deleteNotification(self):
        self.M.select('[Gmail]/Sent Mail')
        search = '(SUBJECT "Generated Notification"'
        search += ' TO "%s")' % self.notifyEmail
        result, data = self.M.uid('search', None, search)
        self.M.uid('store', data[0].split()[-1], '+FLAGS', '\\Deleted')
        self.M.expunge()
