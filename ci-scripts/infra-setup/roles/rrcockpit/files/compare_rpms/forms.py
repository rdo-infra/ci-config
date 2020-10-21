from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, URL


class WebDiffBuilds(FlaskForm):
  control_baseurl = StringField('Control_BaseURL',
                                validators=[DataRequired(), URL()])
  test_baseurl = StringField('Test_BaseURL',
                             validators=[DataRequired(), URL()])
  diff_type = SelectField(u'Diff Type', choices=[('ci_installed',
                                                  'packages installed on nodes'),
                                                 ('all_available',
                                                  'all the packages from enabled repos'),
                                                 ('diff_compose',
                                                  'packages from a compose, not ci job logs')
                                                 ])
  undercloud_only = SelectField(u'Nodes to Diff', choices=[('No', 'use all available nodes'),
                                                           ('Yes', 'only use the undercloud log')
                                                           ])
  submit = SubmitField('Run the Diff')
