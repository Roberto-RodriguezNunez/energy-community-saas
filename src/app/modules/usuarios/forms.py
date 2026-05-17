"""Formularios de Usuario."""
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class EditarUsuarioForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(2, 100)])
    enviar = SubmitField('Guardar')


class PerfilForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(2, 100)])
    enviar = SubmitField('Guardar cambios')
