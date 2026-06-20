import numpy as np
import Fluid_CP as FCP

def recip_comp_corr_SP(param, refrigerant, transcrit=False):

    if transcrit:
        T_ev, p_high, T_3, DeltaT_sh, _D = param # D in mm

        z1_x1=FCP.state(["T","x"],[T_ev,1.],refrigerant,Eh="CBar")
        z_e=FCP.state(["T","p"],[T_ev+DeltaT_sh,z1_x1['p']],refrigerant,Eh="CBar")
        z_as=FCP.state(["p","s"],[p_high,z_e['s']],refrigerant,Eh="CBar")
    else:
        T_ev, T_co, DeltaT_sh, _, _D = param # D in mm

        z1_x1=FCP.state(["T","x"],[T_ev,1.],refrigerant,Eh="CBar")
        z2_x1=FCP.state(["T","x"],[T_co,1.],refrigerant,Eh="CBar")
        z_e=FCP.state(["T","p"],[T_ev+DeltaT_sh,z1_x1['p']],refrigerant,Eh="CBar")
        z_as=FCP.state(["p","s"],[z2_x1['p'],z_e['s']],refrigerant,Eh="CBar")

    b0, b1, a0, a1, a2, a3 = 0.08244, 0.72773, 0.66981, 0.01466, 0.00838, 0.00102

    p_suc = z_e['p'] 
    p_dis = z_as['p']

    p_ratio = p_dis/p_suc

    # volumetric efficiency
    eta_vol = 1. - b0*(p_ratio - 1.)**b1

    # isentrpic efficiency
    eta_is = a0 - (0.6)/((p_ratio - a1)**(a2*(p_suc*1e2))) - a3*p_ratio**1.8

    # mass flow for f_elec = 48.33 Hz and D = 50 mm, H = 39.3 mm, 2 cylinders
    m_dot = 1./z_e['v']*eta_vol*(np.pi/4.*(50.e-3)**2.*(39.3e-3))*48.55/2.*2 # Der Verdichter hat zwei Zylinder aber die mechanische Frequenz entspricht nur der Hälfte der elektrischen Frequenz
    # adapt m_dot to D
    m_dot = m_dot * (_D*1e-3 / 50.e-3) ** 2

    return eta_is, m_dot