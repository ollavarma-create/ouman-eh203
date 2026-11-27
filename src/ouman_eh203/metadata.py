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

# Manuals, page 22: tuning defaults may vary by device.
for prefix,fi,en in [('l1','L1','H1'),('l2','L2','H2'),('dhw','LV','HW')]:
    for suffix,lf,le,limits,default,df,de in [
        ('p_band','P-alue','P-area',[10,300],70 if prefix=='dhw' else 140,
         'Lämpötilapoikkeama, joka vastaa täyttä venttiilin ohjausta.',
         'Temperature deviation corresponding to full valve control.'),
        ('i_time','I-aika','I-time',[5,300],18 if prefix=='dhw' else 50,
         'Aika, jonka kuluessa integraalitoiminto korjaa pysyvää poikkeamaa.',
         'Integration time for correcting persistent deviation.'),
        ('d_time','D-aika','D-time',[0,10],0,
         'Nopeuttaa reagointia lämpötilan muutoksiin; voi aiheuttaa huojuntaa.',
         'Accelerates response to temperature changes; may cause oscillation.'),
    ]:
        key=f'{prefix}_{suffix}'
        _add(key,lf,le,lf,le,22,limits,default)
        PARAMETERS[key].update(access_level='service',
            menu_path=dict(fi=[fi,'Huoltotila','Viritysarvot'],en=[en,'Maint mode','Tuning values']),
            description=dict(fi=df,en=de))
for key,lf,le,limits,default,df,de in [
    ('dhw_feedforward','Ennakoint','Anticipate',[50,250],140,
     'Hyödyntää kiertovesianturia kulutusmuutoksiin reagoimisessa.',
     'Uses circulation sensor readings to respond to consumption changes.'),
    ('dhw_fast_drive','Pika-ajo','Quick run',[0,100],60,
     'Tehostaa reagointia käyttöveden kulutusmuutoksiin.',
     'Enhances response to changes in hot water consumption.'),
]:
    _add(key,lf,le,lf,le,22,limits,default)
    PARAMETERS[key].update(access_level='service',
        menu_path=dict(fi=['LV','Huoltotila','Viritysarvot'],en=['HW','Maint mode','Tuning values']),
        description=dict(fi=df,en=de))
for prefix,fi,en in [('l1','L1','H1'),('l2','L2','H2')]:
    key=f'{prefix}_actuator_time'
    _add(key,'Moottorin ajoaika','Actuator running time',None,None,25,None,150)
    PARAMETERS[key].update(access_level='service',
        menu_path=dict(fi=None,en=[en,'Maint mode','Actuator select']),
        description=dict(fi='Venttiilin ajoaika täysin suljetusta täysin avoimeen asentoon.',
                         en='Time to drive the valve from fully closed to fully open.'),
        dependencies=dict(motor_type_key=f'{prefix}_motor_type'))
    key=f'{prefix}_motor_type'
    _add(key,'Moottorivalinta','Actuator selection',None,'Actuator select',25,None,0)
    PARAMETERS[key].update(access_level='service',
        menu_path=dict(fi=None,en=[en,'Maint mode','Actuator select']),
        choices={0:dict(fi='3-tila 24 VAC',en='3-point 24 VAC'),
                 1:dict(fi='0–10 V',en='0–10 V'),
                 2:dict(fi='2–10 V',en='2–10 V')},
        dependencies=dict(unmapped_manual_option='230 VAC 3-point'))

# Service settings (p. 23); special maintenance settings (p. 29).
for key,fi,en,limits,default,circuit in [
    ('l1_outdoor_delay','Ulkolämpötilan hidastus','OutdoorDelay',[0,20],2,'L1'),
    ('l2_outdoor_delay','Ulkolämpötilan hidastus','OutdoorDelay',[0,20],0,'L2'),
    ('dhw_high_alarm','Käyttöveden hälytysraja','HW alarm',[65,120],65,'LV'),
    ('dhw_boost','Käyttöveden korotus','HW increase',[0,25],0,'LV'),
]:
    _add(key,fi,en,None,en,23,limits,default)
    PARAMETERS[key].update(access_level='service',
        menu_path=dict(fi=[circuit,'Huoltotila','Asetusarvot'],
                       en=[{'L1':'H1','L2':'H2','LV':'HW'}[circuit],'Maint mode','Settings']))
PARAMETERS['dhw_high_alarm']['dependencies']=dict(automatic_limit_increase='dhw_boost',
    manual_default_conflict='p. 23: 65; p. 28: 70')
PARAMETERS['dhw_boost']['dependencies']=dict(schedule='HW increase, clock functions, p. 14')

for key,fi,en,lf,le,limits,default in [
    ('room_delay','Huonelämpötilan hidastus','Room temperature delay','Huonel.hid.','Room delay',[0,2],0.5),
    ('l1_return_max','Paluuveden maksimiraja','Return water maximum','Paluuv.max','RetWat.max',[25,95],70),
    ('l1_return_min_0','Paluuveden minimi 0 °C','Return water minimum at 0 °C','Pal.min (0)','Ret.min (0)',[5,20],5),
    ('l1_return_min_minus20','Paluuveden minimi −20 °C','Return water minimum at −20 °C','Pal.min (-20)','Ret.min (-20)',[10,50],15),
    ('l1_mv_min_0','L1 valmiustilan menoveden minimi 0 °C','H1 standby supply minimum at 0 °C','L1mv Min(0)','H1SuppMin(0)',[5,20],10),
    ('l2_mv_min_0','L2 valmiustilan menoveden minimi 0 °C','H2 standby supply minimum at 0 °C','L2mv Min(0)','H2SuppMin (0)',[5,20],10),
    ('l1_mv_min_minus20','L1 valmiustilan menoveden minimi −20 °C','H1 standby supply minimum at −20 °C','L1mv Min(-20)','H1SupMin(-20)',[10,50],30),
    ('l2_mv_min_minus20','L2 valmiustilan menoveden minimi −20 °C','H2 standby supply minimum at −20 °C','L2mv Min(-20)','H2SupMin(-20)',[10,50],30),
    ('l1_deviation_alarm','L1 poikkeamahälytys','H1 deviation alarm','L1 Poikk.häl','H1 Dev.alarm',[1,75],25),
    ('l2_deviation_alarm','L2 poikkeamahälytys','H2 deviation alarm','L2 Poikk.häl','H2 Dev.alarm',[1,75],25),
    ('dhw_deviation_alarm','LV poikkeamahälytys','HW deviation alarm','LV Poikk.häl','HW Dev.alarm',[1,75],25),
    ('deviation_alarm_delay','Poikkeamahälytyksen hidastus','Deviation alarm delay','PoikHälHid','DevAlaDela',[0,90],60),
    ('power_limit','Tehonrajoitus','Output limit','Tehonraj.','Output lim',[0,999],999),
    ('dhw_alarm_delay','LV-hälytyksen hidastus','HW alarm delay','LV-häl. hid','HW alrm dela',[0,700],600),
    ('r1_outdoor_threshold','R1 ulkolämpötilaraja','Relay 1 outdoor temperature limit',None,'R1 Outd.',[-30,20],-15),
]:
    _add(key,fi,en,lf,le,29,limits,default)
    PARAMETERS[key].update(access_level='special_service',
        menu_path=dict(fi=['Huoltotila','Erikoishuolto','Asetusarvot'],
                       en=['Mainten. mode','Special mainten.','Settings']))
PARAMETERS['room_delay']['dependencies']=dict(used_by='l1_room_gain')
PARAMETERS['r1_outdoor_threshold']['dependencies']=dict(mode='time/outdoor temperature',
    manual_label_conflict='Finnish display example says R2 ulkol.; English says R1 Outd.')
for key in ('l1_deviation_alarm','l2_deviation_alarm','dhw_deviation_alarm'):
    PARAMETERS[key]['dependencies']=dict(delay_key='deviation_alarm_delay')

# Remaining settings. Missing manual evidence stays explicitly unknown.
for key,fi,en,lf,le,page,default,level in [
    ('r1_config','Releen 1 ohjaus','Relay 1 control',None,'Relay1 control',26,None,'service'),
    ('r2_config','Releen 2 ohjaus','Relay 2 control',None,'Relay 2 control',27,None,'service'),
    ('r1_temperature_threshold','R1 lämpöraja','Relay 1 temperature threshold','R1 lämpöraja',None,26,None,'user'),
    ('r1_burner_threshold','Polttimen käynnistysraja','Burner start threshold','Poltin ON',None,26,None,'user'),
    ('r1_burner_hysteresis','Polttimen hystereesi','Burner hysteresis',None,None,26,None,'service'),
    ('pressure_range','Paineen mittausalue','Pressure measurement range','Mittausalue','Meas.area',31,None,'special_service'),
    ('pressure_upper_alarm','Ylärajahälytys','Overpressure alarm','Ylärajahäl.','OverpressAl.',31,2.2,'special_service'),
    ('pressure_filling_alarm','Täyttöhälytys','Fill alarm','Täyttöhäl.','Fill alarm',31,0.7,'special_service'),
    ('pressure_lower_alarm','Alarajahälytys','Lower limit alarm','Alarajahäl.','LowerLimAl.',31,0.5,'special_service'),
    ('consumption_alarm_interval','Kulutushälytyksen tarkkailujakso','Consumption alarm control period','Tarkkjakso','CtrlPeriod',33,0,'special_service'),
    ('pump_indication','Pumpun indikointi','Pump indication',None,None,33,None,'special_service'),
    ('signal_min','Kompensoinnin alaraja','Compensation signal minimum',None,'Min',30,None,'special_service'),
    ('signal_max','Kompensoinnin yläraja','Compensation signal maximum',None,'Max',30,None,'special_service'),
    ('energy_pulse_factor','Energia pulssia kohti','Energy per pulse','KL Energia aset.','DH Energy set',33,None,'special_service'),
    ('district_water_pulse','Kaukolämpövesi pulssia kohti','District heating water per pulse','KL Vesi m3','DH watr metr set',33,None,'special_service'),
    ('consumption_water_pulse','Vedenkulutus pulssia kohti','Water consumption per pulse','Veden kulut. m3','Watr consm set',33,None,'special_service'),
]:
    _add(key,fi,en,lf,le,page,None,default)
    PARAMETERS[key].update(access_level=level)
PARAMETERS['consumption_alarm_interval'].update(manual_range=[0,99],
    description=dict(fi='Hälytys, jos vuorokaudessa ei ole asetetun pituista kulutuksetonta jaksoa. Nolla poistaa toiminnon käytöstä.',
                     en='Alarm if no consumption-free interval of the configured length occurs in 24 hours. Zero disables the function.'))
for key in ('pressure_range','pressure_upper_alarm','pressure_filling_alarm','pressure_lower_alarm'):
    PARAMETERS[key].update(menu_path=dict(fi=['Erikoishuolto','Mitt.6 asetus','Verk.paine'],
                                          en=['Special mainten.','Meas. 6 setting','Network press.']),
                           dependencies=dict(measurement6='network_pressure'))
PARAMETERS['pressure_range']['description']=dict(fi='Mittausalue riippuu lähettimestä ja jännitteenjaosta.',
    en='Measurement range depends on transmitter and voltage divider.')
for key in ('signal_min','signal_max'):
    PARAMETERS[key].update(dependencies=dict(measurement6='external_compensation'),
        menu_path=dict(fi=None,en=['Special mainten.','Meas. 6 setting','E-compensation','Comp/Meas. data']))
PARAMETERS['r1_temperature_threshold']['dependencies']=dict(mode='temperature operated',measurement=11)
for key in ('r1_burner_threshold','r1_burner_hysteresis'):
    PARAMETERS[key]['dependencies']=dict(mode='burner control',measurement=10)
PARAMETERS['r1_burner_hysteresis']['description']=dict(fi='Poltin pysähtyy käynnistysrajan ja hystereesin summassa.',
    en='Burner stops at the start threshold plus hysteresis.')
PARAMETERS['valve_center_close'].update(label=dict(fi='Venttiilin keskisulku (alustava)',en='Valve center close (provisional)'),
    documentation_status='unresolved')

def get_metadata(key):
    """Return a detached metadata record; unknown keys raise KeyError."""
    from copy import deepcopy
    return deepcopy(PARAMETERS[key])
