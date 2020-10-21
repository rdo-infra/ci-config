from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, SubmitField
from wtforms.validators import URL, DataRequired


class WebDiffBuilds(FlaskForm):
    control_baseurl = StringField('Control_BaseURL',
                                  validators=[DataRequired(), URL()])
    test_baseurl = StringField('Test_BaseURL',
                               validators=[DataRequired(), URL()])
    diff_type = SelectField(u'Diff Type',
                            choices=[('ci_installed',
                                      'packages installed on nodes'),
                                     ('all_available',
                                      'all the packages from enabled repos'),
                                     ('diff_compose',
                                      'packages from a compose,\
                                        not ci job logs')
                                     ])
    undercloud_only = BooleanField(u'Only diff the undercloud node'
                                   ' (and the undercloud containers)')
    submit = SubmitField('Run the Diff')
