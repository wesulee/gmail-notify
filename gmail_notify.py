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


def truncate(string, length, omission):
    '''shorten string to length, appending omission to end if shortened'''
    if len(string) <= length:
        return string
    else:
        return string[:length - len(omission)] + omission


def re_encode(string, encoding='ascii'):
    '''return string encoded as encoding
    string may have multiple encodings
    (does not guarantee return preserves whitespace)
    '''
    def encode(string, encoding, re_encode):
        if encoding is None:
            return string
        else:
            return string.decode(encoding).encode(re_encode, 'ignore')

    re_encoded = []
    for string, str_encoding in decode_header(string):
        re_encoded.append(encode(string, str_encoding, encoding))
    return ' '.join(re_encoded)


class Notifier(object):
    def __init__(self, email, password, notifyEmail, settingsDict):
        self.notifyEmail = notifyEmail
        self.settings = settingsDict
        self.login(email, password)
        self.UIDs = self.getUIDs()
        # subject of notification email
        self.notifySubject = 'Generated Notification'

    def login(self, email, password):
        M = imaplib.IMAP4_SSL('imap.gmail.com', '993')
        try:
            M.login(email, password)
            M.select()      # select inbox
            self.loginCred = (email, password)
            self.M = M
        except Exception as e:
            print "Unable to login!"
            raise e

    def getUIDs(self):
        result, data = self.M.uid('search', None, 'ALL')
        if result == 'OK':
            return data[0].split()
        else:
            print "Bad response getting UIDs"

    def getEmail(self, uid):
        '''get a raw email using the uid'''
        result, data = self.M.uid('fetch', uid, '(RFC822)')
        if result == 'OK' and data[0] is not None:
            return data[0][1]
        else:
            print 'Error retrieving email uid: %s' % uid

    def genAllEmails(self):
        '''raw email generator for all retrievable emails in folder'''
        for uid in self.UIDs:
            rawEmail = self.getEmail(uid)
            if rawEmail is not None:
                yield rawEmail

    def formatDate(self, string):
        '''returns the date/time email received into current time
        returns (date, time), date=mm/dd, time=hh:mm AM/PM'''
        t = time.mktime(parsedate(string.split(';')[1].strip()))
        tStr = time.strftime("%m/%d %I:%M %p", time.localtime(t))
        tSplit = tStr.split()
        return tSplit[0], ' '.join(tSplit[1:])

    def getEmailInfo(self, rawEmail):
        '''given a raw email, returns (from, date, time, subject)'''
        email = message_from_string(rawEmail)
        date, time = self.formatDate(email['Received'])
        subject = re_encode(email['Subject'])
        return (re_encode(email['From']), date, time, subject)

    def getAllEmailInfo(self):
        '''get the info of every email in folder'''
        emailData = []
        for rawEmail in self.genAllEmails():
            emailData.append(self.getEmailInfo(rawEmail))
        return emailData

    def createNotification(self, incName=False, incDate=False):
        text = ''
        for address, date, time, subject in self.getAllEmailInfo():
            tmpText = []
            if not incName:                 # remove name from address
                if address.find('<') != -1:
                    address = address[address.index('<') + 1:][:-1]
            tmpText.append(address)
            tmpText.append(truncate(subject, 35, '...'))
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
        msg['Subject'] = self.notifySubject
        server.sendmail(self.loginCred[0], self.notifyEmail, msg.as_string())
        server.quit()

    def deleteEmails(self):
        for uid in self.UIDs:
            self.M.uid('store', uid, '+FLAGS', '\\Deleted')
        self.M.expunge()

    def deleteNotification(self):
        self.M.select('[Gmail]/Sent Mail')
        search = '(SUBJECT "%s"' % self.notifySubject
        search += ' TO "%s")' % self.notifyEmail
        result, data = self.M.uid('search', None, search)
        self.M.uid('store', data[0].split()[-1], '+FLAGS', '\\Deleted')
        self.M.expunge()
