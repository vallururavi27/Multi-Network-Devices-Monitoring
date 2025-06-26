"""
Forms for device management
"""
from django import forms
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, Reset, HTML
from crispy_forms.bootstrap import FormActions
import ipaddress
import pandas as pd
from .models import Device, DeviceGroup, DeviceType


class DeviceForm(forms.ModelForm):
    """Form for creating and editing devices"""
    
    class Meta:
        model = Device
        fields = [
            'name', 'ip_address', 'description', 'device_type', 'location',
            'ping_enabled', 'ping_interval', 'ping_timeout',
            'speed_test_enabled', 'speed_test_interval',
            'alert_enabled', 'alert_threshold_latency', 'alert_threshold_packet_loss',
            'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'ping_interval': forms.NumberInput(attrs={'min': 30, 'max': 3600}),
            'ping_timeout': forms.NumberInput(attrs={'min': 1, 'max': 30}),
            'speed_test_interval': forms.NumberInput(attrs={'min': 300, 'max': 86400}),
            'alert_threshold_latency': forms.NumberInput(attrs={'min': 1, 'max': 10000, 'step': 0.1}),
            'alert_threshold_packet_loss': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': 0.1}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Basic Information',
                Row(
                    Column('name', css_class='form-group col-md-6 mb-0'),
                    Column('ip_address', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                Row(
                    Column('device_type', css_class='form-group col-md-6 mb-0'),
                    Column('location', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                'description',
            ),
            Fieldset(
                'Monitoring Configuration',
                Row(
                    Column('ping_enabled', css_class='form-group col-md-4 mb-0'),
                    Column('ping_interval', css_class='form-group col-md-4 mb-0'),
                    Column('ping_timeout', css_class='form-group col-md-4 mb-0'),
                    css_class='form-row'
                ),
                Row(
                    Column('speed_test_enabled', css_class='form-group col-md-6 mb-0'),
                    Column('speed_test_interval', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
            ),
            Fieldset(
                'Alert Configuration',
                Row(
                    Column('alert_enabled', css_class='form-group col-md-4 mb-0'),
                    Column('alert_threshold_latency', css_class='form-group col-md-4 mb-0'),
                    Column('alert_threshold_packet_loss', css_class='form-group col-md-4 mb-0'),
                    css_class='form-row'
                ),
            ),
            Fieldset(
                'Status',
                'is_active',
            ),
            FormActions(
                Submit('submit', 'Save Device', css_class='btn btn-primary'),
                Reset('reset', 'Reset', css_class='btn btn-secondary'),
                HTML('<a href="{% url "devices:list" %}" class="btn btn-outline-secondary">Cancel</a>'),
            )
        )
    
    def clean_ip_address(self):
        """Validate IP address"""
        ip = self.cleaned_data['ip_address']
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise ValidationError('Invalid IP address format.')
        return ip
    
    def clean(self):
        """Additional form validation"""
        cleaned_data = super().clean()
        
        # Validate ping configuration
        if cleaned_data.get('ping_enabled'):
            if not cleaned_data.get('ping_interval'):
                raise ValidationError('Ping interval is required when ping monitoring is enabled.')
            if not cleaned_data.get('ping_timeout'):
                raise ValidationError('Ping timeout is required when ping monitoring is enabled.')
        
        # Validate speed test configuration
        if cleaned_data.get('speed_test_enabled'):
            if not cleaned_data.get('speed_test_interval'):
                raise ValidationError('Speed test interval is required when speed testing is enabled.')
        
        return cleaned_data


class DeviceGroupForm(forms.ModelForm):
    """Form for creating and editing device groups"""
    
    class Meta:
        model = DeviceGroup
        fields = ['name', 'description', 'color', 'devices']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'color': forms.TextInput(attrs={'type': 'color'}),
            'devices': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Group Information',
                Row(
                    Column('name', css_class='form-group col-md-8 mb-0'),
                    Column('color', css_class='form-group col-md-4 mb-0'),
                    css_class='form-row'
                ),
                'description',
            ),
            Fieldset(
                'Devices',
                'devices',
            ),
            FormActions(
                Submit('submit', 'Save Group', css_class='btn btn-primary'),
                Reset('reset', 'Reset', css_class='btn btn-secondary'),
                HTML('<a href="{% url "devices:group_list" %}" class="btn btn-outline-secondary">Cancel</a>'),
            )
        )


class DeviceSearchForm(forms.Form):
    """Form for searching and filtering devices"""
    
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search devices...',
            'class': 'form-control'
        })
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Device.status.field.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    device_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(DeviceType.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_active = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Row(
                Column('search', css_class='form-group col-md-4 mb-0'),
                Column('status', css_class='form-group col-md-2 mb-0'),
                Column('device_type', css_class='form-group col-md-2 mb-0'),
                Column('is_active', css_class='form-group col-md-2 mb-0'),
                Column(
                    Submit('submit', 'Filter', css_class='btn btn-primary'),
                    css_class='form-group col-md-2 mb-0 d-flex align-items-end'
                ),
                css_class='form-row'
            )
        )


class DeviceImportForm(forms.Form):
    """Form for importing devices from Excel file"""
    
    excel_file = forms.FileField(
        label='Excel File',
        help_text='Upload an Excel file (.xlsx or .xls) with device information',
        widget=forms.FileInput(attrs={
            'accept': '.xlsx,.xls',
            'class': 'form-control'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Import Devices from Excel',
                'excel_file',
                HTML('''
                    <div class="alert alert-info">
                        <h6>Excel File Format:</h6>
                        <p>Your Excel file should contain the following columns:</p>
                        <ul>
                            <li><strong>name</strong> - Device name (required)</li>
                            <li><strong>ip_address</strong> - IP address (required)</li>
                            <li><strong>description</strong> - Description (optional)</li>
                            <li><strong>device_type</strong> - Device type (optional, default: server)</li>
                            <li><strong>location</strong> - Location (optional)</li>
                            <li><strong>ping_enabled</strong> - Enable ping (optional, default: true)</li>
                            <li><strong>alert_enabled</strong> - Enable alerts (optional, default: true)</li>
                        </ul>
                    </div>
                '''),
            ),
            FormActions(
                Submit('submit', 'Import Devices', css_class='btn btn-primary'),
                HTML('<a href="{% url "devices:list" %}" class="btn btn-outline-secondary">Cancel</a>'),
            )
        )
    
    def clean_excel_file(self):
        """Validate Excel file"""
        file = self.cleaned_data['excel_file']
        
        if not file.name.endswith(('.xlsx', '.xls')):
            raise ValidationError('Please upload an Excel file (.xlsx or .xls)')
        
        # Validate file size (max 10MB)
        if file.size > 10 * 1024 * 1024:
            raise ValidationError('File size must be less than 10MB')
        
        # Try to read the Excel file
        try:
            df = pd.read_excel(file)
            
            # Check required columns
            required_columns = ['name', 'ip_address']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValidationError(f'Missing required columns: {", ".join(missing_columns)}')
            
            # Validate data
            if df.empty:
                raise ValidationError('Excel file is empty')
            
            if len(df) > 1000:
                raise ValidationError('Maximum 1000 devices can be imported at once')
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f'Error reading Excel file: {str(e)}')
        
        # Reset file pointer
        file.seek(0)
        return file


class BulkActionForm(forms.Form):
    """Form for bulk actions on devices"""
    
    ACTION_CHOICES = [
        ('enable', 'Enable Monitoring'),
        ('disable', 'Disable Monitoring'),
        ('enable_alerts', 'Enable Alerts'),
        ('disable_alerts', 'Disable Alerts'),
        ('delete', 'Delete Devices'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    device_ids = forms.CharField(widget=forms.HiddenInput())
    
    def clean_device_ids(self):
        """Validate device IDs"""
        device_ids = self.cleaned_data['device_ids']
        try:
            ids = [int(id.strip()) for id in device_ids.split(',') if id.strip()]
            if not ids:
                raise ValidationError('No devices selected')
            return ids
        except ValueError:
            raise ValidationError('Invalid device IDs')
