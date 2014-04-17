#!/usr/bin/env python
#
# hacked up from addcard.py in Doorbot to make it more useful in other apps.
#

from urllib import urlencode
import urllib2, cookielib
from lxml import etree
from lxml.cssselect import CSSSelector
import logging

class addCard:
    def add_card(self, email, password, uid):
        BASE_URL = 'https://london.hackspace.org.uk/'

        cookiejar = cookielib.CookieJar()
        processor = urllib2.HTTPCookieProcessor(cookiejar)
        opener = urllib2.build_opener(processor)
        urllib2.install_opener(opener)

        def browse(url, params=None):
            if params is not None:
                params = urlencode(params)
            page = urllib2.urlopen(BASE_URL + url, params)
            return etree.HTML(page.read())

        find_exception = CSSSelector('.alert')

        login = browse('login.php')
        token = login.xpath('//input[@name="token"]')[0]

        logged_in = browse('login.php', {
            'token': token.attrib['value'],
            'email': email,
            'password': password,
            'submit': 'Log In',
        })

        exc = find_exception(logged_in)
        if exc:
            logging.warn('Could not authenticate')
            logging.warn(etree.tostring(exc[0], method="text", pretty_print=True))
            return (False, etree.tostring(exc[0], method="text", pretty_print=True))

        logout_a = logged_in.xpath('//a[@href="/logout.php"]')
        if not logout_a:
            logging.critical('Could not log in')
            return (False, 'Could not log in')

        addcard = browse('/members/addcard.php')
        token = addcard.xpath('//input[@name="token"]')[0]

        card_added = browse('/members/addcard.php', {
            'token': token.attrib['value'],
            'uid': uid,
            'submit': 'Add',
        })

        exc = find_exception(card_added)
        if exc:
            logging.critical('Could not modify entry')
            logging.critical(etree.tostring(exc[0], method="text", pretty_print=True))
            return (False, etree.tostring(exc[0], method="text", pretty_print=True))

        logging.info("card %s for %s successfully added!" % (uid, email))

        return (True, 'Card Successfully added')
