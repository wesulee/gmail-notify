from gmail_notify import *


# For email login credentials, put email, password, and notification email
# (in that order) in a file separated by new lines. 
with open('credentials.txt', 'rb') as f:
    email, password, notifyEmail = map(lambda x: x.strip(), f.readlines())

# notifyEmail is the SMS gateway (for the phone receiving notifications)
# http://en.wikipedia.org/wiki/List_of_SMS_gateways


# delete emails which a notification has been sent for
deleteAfterNotify = True

# delete the notification from Sent
deleteSent = True

# frequency of updates in minutes
interval = 15


if __name__ == '__main__':
    settings = {'de':deleteAfterNotify, 'dn':deleteSent}
    while True:
        notifier = Notifier(email, password, notifyEmail, settings)
        notifier.sendNotification()
        time.sleep(interval * 60)
