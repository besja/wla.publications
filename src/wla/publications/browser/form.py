# -*- coding: utf-8 -*-

from plone.directives import form

from zope import schema
import z3c.form
from zope.schema.interfaces import IContextSourceBinder
from zope.interface import directlyProvides

from Products.CMFCore.interfaces import ISiteRoot
from Products.statusmessages.interfaces import IStatusMessage

from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile as Zope3PageTemplateFile

from plone.autoform import directives


from wla.publications import _ 


from wla.publications.utils import validateaddress, trusted

from zope.interface import invariant, Invalid
from zope.component import getUtility, getMultiAdapter
from smtplib import SMTPException, SMTPRecipientsRefused
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.interfaces.controlpanel import IMailSchema


from Products.CMFCore.utils import getToolByName
from Products.CMFCore.interfaces import ISiteRoot

from plone.app.uuid.utils import uuidToObject



class IOrderForm(form.Schema):
    """ Define form fields """
    greeting = schema.TextLine(title = _(u'greeting'), required = True) 
    title = schema.TextLine(title = _(u'title'), required = False) 

    lastname = schema.TextLine(title=_(u'Lastname'), required=True)
    firstname = schema.TextLine(title=_(u'Firstname'), required=True)
   
    job = schema.TextLine(title=_(u'Job'), required=False)
    organization = schema.TextLine(title=_(u'Organization'), required=False)
    
    street = schema.TextLine(title=_(u'Street'), required=True)
    number = schema.TextLine(title=_(u'Number'), required=True)
    zipcode = schema.TextLine(title=_(u'Zipcode'), required=True)
    city = schema.TextLine(title=_(u'City'), required=True)
    country = schema.TextLine(title=_(u'Country'), required=True)

    email = schema.TextLine(title=_(u'Email'), required=True, constraint=validateaddress)
    phone = schema.TextLine(title=_(u'Phone'), required=False)
  
    publications = schema.Text(
            title=_(u"publications")
        )


class OrderForm(form.SchemaForm):
    """ Define Form handling

    This form can be accessed as http://yoursite/@@greeting-form

    """
    template = Zope3PageTemplateFile("form.pt")
    schema = IOrderForm
    ignoreContext = True

    def getList(self):
        context = self.context
        path = context.getPhysicalPath()
        items = context.portal_catalog(path={'query': "/".join(path), 'depth': 1},portal_type = 'publication', sort_on='getObjPositionInParent')
        return items

    def _redirect(self, target=''):
        if not target:
            portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
            target = portal_state.portal_url()
        self.request.response.redirect(target)


    @z3c.form.button.buttonAndHandler(_(u'Send'))
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        portal = getToolByName(self, 'portal_url').getPortalObject()
        encoding = portal.getProperty('email_charset', 'utf-8')

        data['image_object'] = uuidToObject(data['image'])
         
        trusted_template = trusted(portal.greeting_email)

        mail_text = trusted_template(self, charset=encoding, data = data)

        subject = self.context.translate(_(u"New greeting"))

        if isinstance(mail_text, unicode):
            mail_text = mail_text.encode(encoding)

        host = getToolByName(self, 'MailHost')

        registry = getUtility(IRegistry)
        mail_settings = registry.forInterface(IMailSchema, prefix='plone')
        m_to = mail_settings.email_from_address

        m_from = m_to

        print m_to

        try:
            host.send(mail_text, m_to, m_from, subject=subject,
                      charset=encoding, immediate=True, msg_type="text/html")

            print m_to

        except SMTPRecipientsRefused:

            raise SMTPRecipientsRefused(
                _(u'Recipient address rejected by server.'))

        except SMTPException as e:
            raise(e)
        
        IStatusMessage(self.request).add(_(u"Submit complete"), type='info')
        return self._redirect(target=self.context.absolute_url())


    @z3c.form.button.buttonAndHandler(_(u"Cancel"))
    def handleCancel(self, action):
        """User cancelled. Redirect back to the front page.
        """