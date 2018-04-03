
import typing
import qailib.common.formbase as formbase
import qailib.common.dataelements as dataelements

# import qailib.transcryptlib.widgets as widgets
import qailib.transcryptlib.htmlelements as html


class HTMLField(formbase.BaseField, html.input):
    def __init__(self, parent: html.base_element, idstr: str,
                 inp_type: str, attrdct: dict) -> None:
        html.input.__init__(self, parent, idstr, inp_type, attrdct)
        formbase.BaseField.__init__(self)
        desc_str = attrdct.get('desc', None)
        if desc_str is not None:
            html.spanhelptext(parent, desc_str)
        self._errfield = html.spanerrortext(parent, "")
        self._is_non_null = (attrdct.get('note', None) == 'non-null')

    def getIDvaltuple(self) -> typing.Tuple[str, str]:
        """Return this input field's id (field name) and current value"""
        self.is_clean()
        return (self.getID(), self._cleaned_data)

    def is_clean(self) -> bool:
        """Perform a check of the user input, producing cleaned up (i.e. checked and converted data)
        from the user input form, and/or generate error messages that
        can be posted to a form for user feedback.
        Return := 'the data is clean'

        NOTE: the cleaned data can be retrieved from self._cleaned_data
        any error messages can be retrieved with  get_error_list() (a list of strings)
        """
        input_str = self.get_stringval()
        clean_dat = self.get_clean_data(input_str)
        return (clean_dat is not None)

    def display_error_list(self, errlst: typing.List[str]) -> None:
        """The subclasses of BaseField should display the list of strings
        concerning errors in the input of this field.
        errlst may be None, in which case the error string is set to the empty string.
        """
        errstr = "" if errlst is None else ", ".join(errlst)
        self._errfield.set_text(errstr)


class StringField(HTMLField, formbase.StringValidateMixin):
    def __init__(self, parent: html.base_element, idstr: str,
                 attrdct: dict) -> None:
        HTMLField.__init__(self, parent, idstr, 'text', attrdct)
        formbase.StringValidateMixin.__init__(self, self._is_non_null)


class EmailField(HTMLField, formbase.EmailValidateMixin):
    def __init__(self, parent: html.base_element, idstr: str,
                 attrdct: dict) -> None:
        HTMLField.__init__(self, parent, idstr, 'text', attrdct)
        formbase.EmailValidateMixin.__init__(self)


class IntField(HTMLField, formbase.IntValidateMixin):
    def __init__(self, parent: html.base_element, idstr: str,
                 attrdct: dict) -> None:
        HTMLField.__init__(self, parent, idstr, 'text', attrdct)
        formbase.IntValidateMixin.__init__(self, None)


class CheckBoxField(HTMLField, formbase.BaseValidateMixin):
    def __init__(self, parent: html.base_element, idstr: str,
                 attrdct: dict) -> None:
        HTMLField.__init__(self, parent, idstr, 'checkbox', attrdct)
        formbase.BoolValidateMixin.__init__(self)


class HtmlFormBuilder(formbase.BaseFormBuilder):

    def __init__(self, formdef_dct: dict) -> None:
        super().__init__(formdef_dct)
        tt = self._type_handler_dct = {}
        tt['QLUserRoleTag'] = self._gen_roletag

    @staticmethod
    def _gen_roletag(parent: html.element, ddct: dict, val: typing.Any) -> HTMLField:
        """Generate a role:tag combo string."""
        if val is None:
            tr_string = None
        else:
            print("VALL {}".format(val))
            roleval = val['role']
            tagval = val['tag']['tagname']
            tr_string = "{}:{}".format(tagval, roleval)
        #
        attdct = None if tr_string is None else dict(value=tr_string)
        # namestr = "{}-inp".format(ddct.get('name', 'noname'))
        namestr = "{}".format(ddct.get('name', 'noname'))
        return html.input(parent, namestr, 'text', attdct)

    def _scal_el(self, parent: html.element, ddct: dict, val: typing.Any) -> HTMLField:
        type_str = ddct.get('type', None)
        cls_dct = dict(Boolean=CheckBoxField)
        attdct = {} if val is None else dict(value=str(val))
        desc_str = ddct.get('desc', None)
        if desc_str is not None:
            attdct['desc'] = desc_str
        namefield = ddct.get('name', 'noname')
        # namestr = "{}-inp".format(namefield)
        namestr = "{}".format(namefield)
        field_class_type = cls_dct.get(type_str, None)
        if field_class_type is None:
            if namefield == 'email':
                print('GOT EMAIL')
                return EmailField(parent, namestr, attdct)
            else:
                return StringField(parent, namestr, attdct)
        else:
            print('fieldy {}'.format(type_str))
            return field_class_type(parent, namestr, attdct)

    def _input_el(self, parent: html.element, ddct: dict, val: typing.Any) -> HTMLField:
        type_str = ddct.get('type', None)
        kind_str = ddct.get('kind', None)
        note_str = ddct.get('note', None)
        if kind_str == 'SCALAR':
            retval = self._scal_el(parent, ddct, val)
        elif kind_str == 'OBJECT' or kind_str == 'INPUT_OBJECT':
            cust_func = self._type_handler_dct.get(type_str, None)
            if cust_func is not None:
                if note_str == 'list':
                    # namestr = "{}-inp".format(ddct.get('name', 'noname'))
                    namestr = "{}".format(ddct.get('name', 'noname'))
                    retval = html.input_list(parent, namestr, None)
                    for valdct in val:
                        retval.addItem(cust_func(parent, ddct, valdct))
                else:
                    retval = cust_func(parent, ddct, val)
            else:
                print("cannot handle non-custom OBJECT")
                retval = None
                # a list of items of type type_str
                # retval = self._list_el(parent, ddct, val)
        else:
            print("HTML:UNKNOWN kind '{}'".format(kind_str))
            retval = self._scal_el(parent, ddct, val)
        #
        return retval

    def gen_table(self,
                  parent: html.element,
                  tabid: str,
                  attrdct: dict,
                  data: dataelements.record) -> typing.Tuple[html.table, typing.List[HTMLField]]:
        """Generate an html table element containing the form elements
        defined in this class.
        The list of HTMLField are returned separately for ease of input validation.
        The form elements will be filled in from the data record whenever possible.
        Setting data to None will print an empty form.
        """
        if self._dct_lst is None:
            return None, None
        tab = html.table(parent, tabid, attrdct)
        print("GENTABBY {}".format(data))
        inp_lst = []
        for varname, dct in self._dct_lst:
            print("GENF {}: {}".format(varname, dct))
            row = html.tr(tab, "{}-row{}".format(tabid, varname), None)
            # left column: variable name: use a th
            th = html.th(row, "{}-rowh{}".format(tabid, varname), None)
            html.textnode(th, varname)
            # now the data field: use a td
            datvar = None if data is None else data[varname]
            td = html.td(row, "{}-rowd{}".format(tabid, varname), None)
            inp = self._input_el(td, dct, datvar)
            if inp is not None:
                inp_lst.append(inp)
        return tab, inp_lst
