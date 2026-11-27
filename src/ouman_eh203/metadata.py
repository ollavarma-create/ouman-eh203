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

# Curve coordinates: labels are presentation labels, not literal LCD strings.
for prefix,fi,en in [('l1','L1','H1'),('l2','L2','H2')]:
    for axis,indices in [('y',range(1,6)),('x',(2,3,4))]:
        for i in indices:
            key=f'{prefix}_curve_{axis}{i}'
            y=axis=='y'
            _add(key,None,None,None,None,4)
            PARAMETERS[key].update(
                label=dict(fi=f'{"Menoveden" if y else "Ulkolämpötilan"} asetus, piste {i}',
                           en=f'{"Supply water" if y else "Outdoor temperature"} setting, point {i}'),
                lcd_label=dict(fi=None,en=None),
                menu_path=dict(fi=[fi,'Säätökäyrien as'],en=[en,'Heating curve']),
                manual_range=[5,120] if y else None,
                manual_page=dict(fi=5,en=4),
                factory_default=None,
                dependencies=dict(curve_type_key=f'{prefix}_curve_type',
                                  visible_values=[0] if not y or i in (2,4) else [0,1]),
                documentation_status='partial')
    key=f'{prefix}_curve_type'
    _add(key,'Säätökäyrän tyyppi','Heating curve type','Käyrätyyppi','Curve type',34)
    PARAMETERS[key].update(access_level='special_service',
        menu_path=dict(fi=None,en=['Mainten. mode','Special mainten.','Curve type']),
        factory_default=1, choices={0:dict(fi='5-piste',en='5-point'),1:dict(fi='3-piste',en='3-point')},
        dependencies=dict(shared_with='l2_curve_type' if prefix=='l1' else 'l1_curve_type'))

def get_metadata(key):
    """Return a detached metadata record; unknown keys raise KeyError."""
    from copy import deepcopy
    return deepcopy(PARAMETERS[key])
