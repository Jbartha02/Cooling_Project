# -*- coding: utf-8 -*-
"""
Created on Fri Dec 17 10:05:26 2021

@author: Dr. Dennis Roskosch

Interface between Python and CoolProp database.
It is compulsory to first install CoolProp--> pip install CoolProp
Script includes to functions for external call:
    state --> call os state variables
    get_fluid_info --> returns fluid information
"""

from pylab import *
import CoolProp.CoolProp as CP
import pandas as pd

dTk=273.15

index=["T","p","v","u","h","s","x"]


def state(Var,In,fluid,Eh="CBar"):
    
    """
    Function to calculate stae variables of a thermodynamic state defined by two state variables.
    
    Inputs:
        Var: List containing two strings of symbols of the state that will be inserted, e.g., ["T","s"] -> Input: temperature and spec. entropy
        In: List of values of the state variables defined in Var
        fluid: String of the fluid name as defined in the documentation
        Eh: String defining the unit system
    
    Supported input combinations of Var
         ["T","p"]  temperature, pressure   
         ["T","x"]  temperature, steam quality
         ["T","v"]  temperature, spec. volume
         ["p","v"]  pressure, spec. volume
         ["p","x"]  pressure, steam quality
         ["p","h"]  pressure, spec. enthalpy
         ["p","s"]  pressure, spec. entropy
         ["h","s"]  pressure, spec. entropy
         ["u","v"]  spec. internal energy, spec. volume
         The order in Var doesn't matter
    
    Standard outputs
        T    temperature                        
        p    pressure                             
        v    spec. volume                        
        u    spec. internal energy                
        h    spec. enthalpy                      
        s    spec. entrop                         
        x    steam quality                       
        The function returns a pandas series.                       
        
    Units for in- and output, defined by Eh
    
       Eh=   "SI"     "CBar"   "CKPa"  
                      ¦        ¦        
        T     K        C        C       
        p     Pa       bar      kPa      
        v     m3/kg    m3/kg    m3/kg   
        u     J/kg     kJ/kg    kJ/kg    
        h     J/kg     kJ/kg    kJ/kg    
        s     J/kg/K   kJ/kg/K  kJ/kg/K  
        x     kg/kg    kg/kg    kg/kg    
    
    """
    
    # T und p
    if Var[0]=="T" and Var[1]=="p":
        if Eh=="CBar":
            T=In[0]+dTk
            p=In[1]*1e5
        elif Eh=="CKPa":
            T=In[0]+dTk
            p=In[1]*1e3
        else:
            T=In[0]
            p=In[1]
        h=CP.PropsSI("H","T",T,"P",p,fluid)        
    # p und T
    if Var[0]=="p" and Var[1]=="T":
        if Eh=="CBar":
            T=In[1]+dTk
            p=In[0]*1e5
        elif Eh=="CKPa":
            T=In[1]+dTk
            p=In[0]*1e3
        else:
            T=In[1]
            p=In[0]
        h=CP.PropsSI("H","T",T,"P",p,fluid)

    ###########################################################       
    # T and x
    if Var[0]=="T" and Var[1]=="x":
        if Eh=="CBar":
            T=In[0]+dTk
            x=In[1]
        elif Eh=="CKPa":
            T=In[0]+dTk
            x=In[1]
        else:
            T=In[0]
            x=In[1]
        h=CP.PropsSI("H","T",T,"Q",x,fluid)
        p=CP.PropsSI("P","T",T,"Q",x,fluid)
    # x and T
    if Var[0]=="x" and Var[1]=="T":
        if Eh=="CBar":
            T=In[1]+dTk
            x=In[0]
        elif Eh=="CKPa":
            T=In[1]+dTk
            x=In[0]
        else:
            T=In[1]
            x=In[0]
        h=CP.PropsSI("H","T",T,"Q",x,fluid)
        p=CP.PropsSI("P","T",T,"Q",x,fluid)

##############################################################
    # p and x
    if Var[0]=="p" and Var[1]=="x":
        if Eh=="CBar":
            p=In[0]*1e5
            x=In[1]
        elif Eh=="CKPa":
            p=In[0]*1e3
            x=In[1]
        else:
            p=In[0]
            x=In[1]
        h=CP.PropsSI("H","P",p,"Q",x,fluid)
        T=CP.PropsSI("T","P",p,"Q",x,fluid)
    # x and p
    if Var[0]=="x" and Var[1]=="p":
        if Eh=="CBar":
            p=In[1]*1e5
            x=In[0]
        elif Eh=="CKPa":
            p=In[1]*1e3
            x=In[0]
        else:
            p=In[1]
            x=In[0]
        h=CP.PropsSI("H","P",p,"Q",x,fluid)
        T=CP.PropsSI("T","P",p,"Q",x,fluid)
##############################################################          
# p and h
    if Var[0]=="p" and Var[1]=="h":
        if Eh=="CBar":
            p=In[0]*1e5
            h=In[1]*1000.
        elif Eh=="CKPa":
            p=In[0]*1e3
            h=In[1]*1000.
        else:
            p=In[0]
            h=In[1]
        T=CP.PropsSI("T","P",p,"H",h,fluid)
    # h and p
    if Var[0]=="h" and Var[1]=="p":
        if Eh=="CBar":
            p=In[1]*1e5
            h=In[0]*1000.
        elif Eh=="CKPa":
            p=In[1]*1e3
            h=In[0]*1000.
        else:
            p=In[1]
            h=In[0]
        T=CP.PropsSI("T","P",p,"H",h,fluid)
#################################################################♠
    # p and s
    if Var[0]=="p" and Var[1]=="s":
        if Eh=="CBar":
            p=In[0]*1e5
            s=In[1]*1000.
        elif Eh=="CKPa":
            p=In[0]*1e3
            s=In[1]*1000.
        else:
            p=In[0]
            s=In[1]
        h=CP.PropsSI("H","P",p,"S",s,fluid)
        T=CP.PropsSI("T","P",p,"S",s,fluid)
    # s and p
    if Var[0]=="s" and Var[1]=="p":
        if Eh=="CBar":
            p=In[1]*1e5
            s=In[0]*1000.
        elif Eh=="CKPa":
            p=In[1]*1e3
            s=In[0]*1000.
        else:
            p=In[1]
            s=In[0]
        h=CP.PropsSI("H","P",p,"S",s,fluid)
        T=CP.PropsSI("T","P",p,"S",s,fluid)
##############################################################  
    # T and s
    if Var[0]=="T" and Var[1]=="s":
        if Eh=="CBar":
            T=In[0]+dTk
            s=In[1]*1000.
        elif Eh=="CKPa":
            T=In[0]+dTk
            s=In[1]*1000.
        else:
            T=In[0]
            s=In[1]
        h=CP.PropsSI("H","T",T,"S",s,fluid)
        p=CP.PropsSI("P","T",T,"S",s,fluid)
    # s and T
    if Var[0]=="s" and Var[1]=="T":
        if Eh=="CBar":
            T=In[1]+dTk
            s=In[0]*1000.
        elif Eh=="CKPa":
            T=In[1]+dTk
            s=In[0]*1000.
        else:
            T=In[1]
            s=In[0]
        h=CP.PropsSI("H","T",T,"S",s,fluid)
        p=CP.PropsSI("P","T",T,"S",s,fluid)
##############################################################  

    # h and s
    if Var[0]=="h" and Var[1]=="s":
        if Eh=="CBar":
            h=In[0]*1e3
            s=In[1]*1000.
        elif Eh=="CKPa":
            h=In[0]*1e3
            s=In[1]*1000.
        else:
            h=In[0]
            s=In[1]
        T=CP.PropsSI("T","H",h,"S",s,fluid)
        p=CP.PropsSI("P","H",h,"S",s,fluid)
    # s and h
    if Var[0]=="s" and Var[1]=="h":
        if Eh=="CBar":
            h=In[1]*1e3
            s=In[0]*1000.
        elif Eh=="CKPa":
            h=In[1]*1e3
            s=In[0]*1000.
        else:
            h=In[1]
            s=In[0]
        T=CP.PropsSI("T","H",h,"S",s,fluid)
        p=CP.PropsSI("P","H",h,"S",s,fluid)
##############################################################    
    # T und v
    if Var[0]=="T" and Var[1]=="v":
        if Eh=="CBar":
            T=In[0]+dTk
            v=In[1]
        elif Eh=="CKPa":
            T=In[0]+dTk
            v=In[1]
        else:
            T=In[0]
            v=In[1]
        p=CP.PropsSI("P","T",T,"D",1./v,fluid)
        h=CP.PropsSI("H","T",T,"D",1./v,fluid)    

    # v und T
    if Var[0]=="v" and Var[1]=="T":
        if Eh=="CBar":
            T=In[1]+dTk
            v=In[0]
        elif Eh=="CKPa":
            T=In[1]+dTk
            v=In[0]
        else:
            T=In[1]
            v=In[0]
        p=CP.PropsSI("P","T",T,"D",1./v,fluid)
        h=CP.PropsSI("H","T",T,"D",1./v,fluid)  

##############################################################
    # p und v
    if Var[0]=="p" and Var[1]=="v":
        if Eh=="CBar":
            p=In[0]*1e5
            v=In[1]
        elif Eh=="CKPa":
            p=In[0]*1e3
            v=In[1]
        else:
            p=In[0]
            v=In[1]
        T=CP.PropsSI("T","P",p,"D",1./v,fluid)
        h=CP.PropsSI("H","P",p,"D",1./v,fluid)  
    # v und p
    if Var[0]=="v" and Var[1]=="p":
        if Eh=="CBar":
            p=In[1]*1e5
            v=In[0]
        elif Eh=="CKPa":
            p=In[1]*1e3
            v=In[0]
        else:
            p=In[1]
            v=In[0]
        T=CP.PropsSI("T","P",p,"D",1./v,fluid)
        h=CP.PropsSI("H","P",p,"D",1./v,fluid)  
####################################################################   
    # u und v
    if Var[0]=="u" and Var[1]=="v":
        if Eh=="CBar":
            u=In[0]*1e3
            v=In[1]
        elif Eh=="CKPa":
            u=In[0]*1e3
            v=In[1]
        else:
            u=In[0]
            v=In[1]
        p=CP.PropsSI("P","U",u,"D",1./v,fluid)
        h=CP.PropsSI("H","U",u,"D",1./v,fluid)  
        T=CP.PropsSI("T","P",p,"D",1./v,fluid)
    # v und p
    if Var[0]=="v" and Var[1]=="u":
        if Eh=="CBar":
            u=In[1]*1e3
            v=In[0]
        elif Eh=="CKPa":
            u=In[1]*1e3
            v=In[0]
        else:
            u=In[1]
            v=In[0]
        p=CP.PropsSI("P","U",u,"D",1./v,fluid)
        h=CP.PropsSI("H","U",u,"D",1./v,fluid)  
        T=CP.PropsSI("T","P",p,"D",1./v,fluid)
####################################################################      
   

    ## Remaining variables
    v=1./CP.PropsSI("D","P",p,"H",h,fluid)
    u=CP.PropsSI("U","P",p,"H",h,fluid)
    s=CP.PropsSI("S","P",p,"H",h,fluid)
    x=CP.PropsSI("Q","P",p,"H",h,fluid)
    
    ## Check phase
    info=get_fluid_info(fluid,"SI")
    if info["p_crit"]>=p:
        h0=CP.PropsSI("H","P",p,"Q",0,fluid)
        h1=CP.PropsSI("H","P",p,"Q",1,fluid)
        if h>h1: x=998. #superheated
        elif h<h0: x=-998 #subcooled
    else:
        x=998.
    
    ## Changing units
    if Eh=="CBar":
        T=T-dTk
        p=p*1e-5
        u=u*1e-3
        h=h*1e-3
        s=s*1e-3
    elif Eh=="CKPa":
        T=T-dTk
        p=p*1e-3
        u=u*1e-3
        h=h*1e-3
        s=s*1e-3
    
    state=pd.Series([T,p,v,u,h,s,x],index=index)
    return state



def get_fluid_info(fluid, Eh="CBar"):
    """Function to request standard fluid properties
    Inputs:
        fluid: String of the fluid name as defined in the documentation
        Eh: String defining the unit system
    Outputs (pandas series):
        Molar mass, molar_mass
        Critical temperature, T_crit
        Critical pressure, p_crit
        Acentric factor, acentric
        Minimum allowed temperature, T_min
        Maximum allowed temperature, T_max
    Units for in- and output, defined by Eh
    
       Eh=   "SI"     "CBar"   "CKPa"  
                      ¦        ¦        
        T     K        C        C       
        p     Pa       bar      kPa      
        v     m3/kg    m3/kg    m3/kg   
    """
    
    M=CP.PropsSI("M",fluid)
    Tc=CP.PropsSI("Tcrit",fluid)
    pc=CP.PropsSI("pcrit",fluid)
    om=CP.PropsSI("acentric",fluid)
    Tmin=CP.PropsSI("TMIN",fluid)
    Tmax=CP.PropsSI("TMAX",fluid)
    
    if Eh=="CBar":
        Tc=Tc-dTk
        pc=pc*1e-5
        Tmin=Tmin-dTk
        Tmax=Tmax-dTk
    elif Eh=="CKPa":
        Tc=Tc-dTk
        pc=pc*1e-3
        Tmin=Tmin-dTk
        Tmax=Tmax-dTk
    info=pd.Series([M,Tc,pc,om,Tmin,Tmax],\
       index=["molar_mass","T_crit","p_crit","acentric","T_min","T_max"])
    return info
  

