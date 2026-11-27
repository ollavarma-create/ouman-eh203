"""Presentation metadata, never a write authorization."""
from .registry import FIELDS

def _entry(key, fi, en, lcd_fi, lcd_en, page, limits=None, default=None, circuit=None):
    return dict(key=key, label=dict(fi=fi,en=en),
                lcd_label=dict(fi=lcd_fi,en=lcd_en),
                description=dict(fi=None,en=None),
                menu_path=dict(fi=[circuit,'Asetusarvot'] if circuit else None,
                               en=[{'L1':'H1','L2':'H2','LV':'HW'}[circuit],'Settings'] if circuit else None),
                access_level='user',manual_page=dict(fi=page,en=page),
                manual_range=limits,factory_default=default,
                dependencies=None,write_policy='restore_validator_only',
                documentation_status='partial')

PARAMETERS={key:dict(key=key,label=dict(fi=None,en=None),
    lcd_label=dict(fi=None,en=None),description=dict(fi=None,en=None),
    menu_path=dict(fi=None,en=None),access_level=None,
    manual_page=dict(fi=None,en=None),manual_range=None,factory_default=None,
    dependencies=None,write_policy='restore_validator_only',
    documentation_status='pending') for key,*_ in FIELDS}

def _add(key,*args,**kwargs):
    if key not in PARAMETERS:
        raise ValueError(key)
    PARAMETERS[key]=_entry(key,*args,**kwargs)

for prefix,circuit in [('l1','L1'),('l2','L2')]:
    for suffix,fi,en,lf,le,page,limits,default in [
        ('supply_min','Menoveden minimiraja','Minimum supply temperature','Minimiraja','Min.limit',6,[5,70],15),
        ('supply_max','Menoveden maksimiraja','Maximum supply temperature','Maksimiraja','Max.limit',6,[15,125],70),
        ('night_reduction','Menoveden yöalennus','Supply temperature reduction','Yöalennus v.','Temp drop(w)',6,[0,35],0),
        ('parallel_shift','Suuntaissiirto','Parallel shift','Suuntaiss.','Parall.shift',6,[-15,15],0),
        ('autumn_drying','Syyskuivaus','Autumn drying','Syyskuivaus','Autumn dry',7,[0,15],2),
    ]:
        _add(prefix+'_'+suffix,fi,en,lf,le,page,limits,default,circuit)
_add('l1_room_setpoint','Huonelämpötilan asetus','Room temperature setting','Huonelämpö','Room temp.',6,[5,45],21.5,'L1')
_add('l1_room_gain','Huonekompensointisuhde','Room compensation ratio','Huonekomp.s','RoomCompens.',6,[0,7],4,'L1')
_add('dhw_setpoint','Käyttöveden lämpötila','Domestic hot water temperature','Käyttövesi','DomHot wat.',7,[5,95],58,'LV')

def get_metadata(key):
    """Return a detached metadata record; unknown keys raise KeyError."""
    from copy import deepcopy
    return deepcopy(PARAMETERS[key])
