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
from scipy.optimize import brentq, fsolve

dTk=273.15

index=["T","p","v","u","h","s","x"]

T0=0.01+dTk
p0=611.7


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
    h0=CP.PropsSI("H","T",T0,"P",p0,fluid)  
    s0=CP.PropsSI("S","T",T0,"P",p0,fluid)
    u0=CP.PropsSI("U","T",T0,"P",p0,fluid)
    
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
    
    x=nan
    
    ## Changing units
    if Eh=="CBar":
        T=T-dTk
        p=p*1e-5
        u=u*1e-3
        h=h*1e-3
        h0=h0*1e-3
        s0=s0*1e-3
        u0=u0*1e-3
        s=s*1e-3
    elif Eh=="CKPa":
        T=T-dTk
        p=p*1e-3
        u=u*1e-3
        h=h*1e-3
        s=s*1e-3
        h0=h0*1e-3
        s0=s0*1e-3
        u0=u0*1e-3
    
    state=pd.Series([T,p,v,u,h-h0,s-s0,x],index=index)
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
  

index_m=["T","X","phi","h*","v*"]

def state_moist(Var,In):
    """
    Function to calculate stae variables of a thermodynamic state of moist air defined by two state variables.
    Only valif for p=1bar and not oversaturated states
    
    Inputs:
        Var: List containing two strings of symbols of the state that will be inserted, e.g., ["T","phi"] -> Input: temperature and humidity
        In: List of values of the state variables defined in Var
    
    Supported input combinations of Var
         ["T","X"]     temperature, water content   
         ["T","phi"]   temperature, humidity
         ["T","h*"]    temperature, enthalpy spec. to air mass
         ["X","phi"]   water content, humidity
         ["X","h*"]    water content, enthalpy spec. to air mass
         ["phi","h*"]  humidity, enthalpy spec. to air mass
         The order in Var doesn't matter
    
    Standard outputs
        T    temperature                        
        X    water content       
        phi  humidity                        
        h*   enthalpy spec. to air mass   
        v*   specific volume (Volume of moist air related to mass of dry air)                
                     
        
    Units for in- and output, defined by Eh
    
        
        T     °C                 
        X     kg_w/kg_a        
        phi   -     
        h*    kJ/kg_a     
        v*    m3 moist air / kg dry air

    """
    T0=0.01+dTk
    p0=611.7
        
    Eh="CBar"
    p=1.
    
    Tmax=50.
    Tsch=25.
    
    h_a0=state(["T","p"],[T0-dTk,p*1e-5],"air",Eh)["h"]
    h_w0=state(["T","p"],[T0-dTk,p0*1e-5],"water",Eh)["h"]    
    
##########################################################################   
    if Var[0]=="T" and Var[1]=="X":
        T=In[0]
        X=In[1]
        psat=state(["T","x"],[T,0.],"water",Eh)["p"]
        phi=X*p/(psat*(0.622+X))
        if phi>1.:
            print("State is oversaturated")
            phi=nan
            h=nan
        elif phi==0.:
            h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
            h=h_a
        elif phi==1.:
            h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
            h_w=state(["T","x"],[T,1.],"water",Eh)["h"]-h_w0
            h=h_a+X*h_w
        else:
            p_w=phi*psat      
            h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
            h_w=state(["T","p"],[T,p_w],"water",Eh)["h"]-h_w0
            h=h_a+X*h_w
            
    elif Var[0]=="X" and Var[1]=="T":
        T=In[1]
        X=In[0]
        psat=state(["T","x"],[T,0.],"water",Eh)["p"]
        phi=X*p/(psat*(0.622+X))
        if phi>1.:
            print("State is oversaturated")
            phi=nan
            h=nan
        elif phi==0.:
            h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
            h=h_a
        elif phi==1.:
            h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
            h_w=state(["T","x"],[T,1.],"water",Eh)["h"]-h_w0
            h=h_a+X*h_w
        else:
            p_w=phi*psat      
            h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
            h_w=state(["T","p"],[T,p_w],"water",Eh)["h"]-h_w0
            h=h_a+X*h_w
            
##########################################################################       
    elif Var[0]=="T" and Var[1]=="phi":
        T=In[0]
        phi=In[1]
        if phi>=0. and phi<=1.:
            h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
            if phi==0.:
                h=h_a
                X=0
            else:
                psat=state(["T","x"],[T,0.],"water",Eh)["p"]
                X=.622*psat/(p/phi-psat)
                if phi==1.:
                    h_w=state(["T","x"],[T,1.],"water",Eh)["h"]-h_w0
                else:
                    p_w=phi*psat      
                    h_w=state(["T","p"],[T,p_w],"water",Eh)["h"]-h_w0
                h=h_a+X*h_w            
        else:
            print("State is oversaturated")
            X=nan
            h=nan
            
    elif Var[0]=="phi" and Var[1]=="T":
        T=In[1]
        phi=In[0]
        if phi>=0. and phi<=1.:
            h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
            if phi==0.:
                h=h_a
                X=0
            else:
                psat=state(["T","x"],[T,0.],"water",Eh)["p"]
                X=.622*psat/(p/phi-psat)
                if phi==1.:
                    h_w=state(["T","x"],[T,1.],"water",Eh)["h"]-h_w0
                else:
                    p_w=phi*psat      
                    h_w=state(["T","p"],[T,p_w],"water",Eh)["h"]-h_w0
                h=h_a+X*h_w            
        else:
            print("State is oversaturated")
            X=nan
            h=nan
            
##########################################################################         
    elif Var[0]=="T" and Var[1]=="h*":
        T=In[0]
        h=In[1]
        psat=state(["T","x"],[T,0.],"water",Eh)["p"]
        X0=0.
        X1=.622*psat/(p-psat)
        def help1(X):
            h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
            if X==0.:
                h_=h_a
            else:
                phi=X*p/(psat*(0.622+X))
                p_w=phi*psat             
                if round(phi,2)==1.:
                    h_w=state(["T","x"],[T,1.],"water",Eh)["h"]-h_w0
                else:
                    h_w=state(["T","p"],[T,p_w],"water",Eh)["h"]-h_w0
                h_=h_a+X*h_w
            return h_-h
        try:
            X=brentq(help1,X0,X1)
            phi=X*p/(psat*(0.622+X))
        except:
            print("State is oversaturated")
            X=nan
            phi=nan
            
    elif Var[0]=="h*" and Var[1]=="T":
        T=In[1]
        h=In[0]
        psat=state(["T","x"],[T,0.],"water",Eh)["p"]
        X0=0.
        X1=.622*psat/(p-psat)
        def help1(X):
            h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
            if X==0.:
                h_=h_a
            else:
                phi=X*p/(psat*(0.622+X))
                p_w=phi*psat             
                if round(phi,2)==1.:
                    h_w=state(["T","x"],[T,1.],"water",Eh)["h"]-h_w0
                else:
                    h_w=state(["T","p"],[T,p_w],"water",Eh)["h"]-h_w0
                h_=h_a+X*h_w
            return h_-h
        try:
            X=brentq(help1,X0,X1)
            phi=X*p/(psat*(0.622+X))
        except:
            print("State is oversaturated")
            X=nan
            phi=nan
            
###############################################################################    
    elif Var[0]=="phi" and Var[1]=="X":
        phi=In[0]
        X=In[1]
        if phi>1:
            print("State is oversaturated")
            T=nan
            h=nan
        else:
            psat=X*p/phi/(.622+X)
            T=state(["p","x"],[psat,0.],"water",Eh)["T"]
            if phi>1.:
                print("State is oversaturated")
                phi=nan
                h=nan
            elif phi==0.:
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h=h_a
            elif round(phi,2)==1.:
                p_w=psat
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_w=state(["T","x"],[p_w,1.],"water",Eh)["h"]-h_w0
                h=h_a+X*h_w
            else:
                p_w=phi*psat      
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_w=state(["T","p"],[T,p_w],"water",Eh)["h"]-h_w0
                h=h_a+X*h_w
              
                
    elif Var[0]=="X" and Var[1]=="phi":
        phi=In[1]
        X=In[0]
        if phi>1:
            print("State is oversaturated")
            T=nan
            h=nan
        else:
            psat=X*p/phi/(.622+X)
            print(psat)
            T=state(["p","x"],[psat,0.],"water",Eh)["T"]
            if phi>1.:
                print("State is oversaturated")
                phi=nan
                h=nan
            elif phi==0.:
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h=h_a
            elif round(phi,2)==1.:
                p_w=psat
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_w=state(["T","x"],[p_w,1.],"water",Eh)["h"]-h_w0
                h=h_a+X*h_w
            else:
                p_w=phi*psat      
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_w=state(["T","p"],[T,p_w],"water",Eh)["h"]-h_w0
                h=h_a+X*h_w

#################################################################################
    elif Var[0]=="X" and Var[1]=="h*":
        X=In[0]
        h=In[1]
        
        def help2(T):
            psat=state(["T","x"],[T,0.],"water",Eh)["p"]
            phi=X*p/(psat*(0.622+X))
            if phi==0.:
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_=h_a
            elif round(phi,2)==1.:
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_w=state(["T","x"],[T,1.],"water",Eh)["h"]-h_w0
                h_=h_a+X*h_w
            else:
                p_w=phi*psat      
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_w=state(["T","p"],[T,p_w],"water",Eh)["h"]-h_w0
                h_=h_a+X*h_w
            return h_-h
        
        psat0=X*p/(.622+X)
        T0=state(["p","x"],[psat0,0.],"water",Eh)["T"]
        try:
            T=brentq(help2,T0,Tmax)
            psat=state(["T","x"],[T,0.],"water",Eh)["p"]
            phi=X*p/(psat*(0.622+X))
        except:
            print("State is oversaturated")
            T=nan
            phi=nan
            
        
    elif Var[0]=="h*" and Var[1]=="X":
        X=In[1]
        h=In[0]
        
        def help2(T):
            psat=state(["T","x"],[T,0.],"water",Eh)["p"]
            phi=X*p/(psat*(0.622+X))
            if phi==0.:
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_=h_a
            elif round(phi,2)==1.:
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_w=state(["T","x"],[T,1.],"water",Eh)["h"]-h_w0
                h_=h_a+X*h_w
            else:
                p_w=phi*psat      
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_w=state(["T","p"],[T,p_w],"water",Eh)["h"]-h_w0
                h_=h_a+X*h_w
            return h_-h
        
        psat0=X*p/(.622+X)
        T0=state(["p","x"],[psat0,0.],"water",Eh)["T"]
        try:
            T=brentq(help2,T0,Tmax)
            psat=state(["T","x"],[T,0.],"water",Eh)["p"]
            phi=X*p/(psat*(0.622+X))
        except:
            print("State is oversaturated")
            T=nan
            phi=nan
            
##################################################################################
    elif Var[0]=="phi" and Var[1]=="h*":
        phi=In[0]
        h=In[1]
        
        def help2(T_):
            #T=T_[0]
            T=T_
            psat=state(["T","x"],[T,0.],"water",Eh)["p"]
            X=.622*psat/(p/phi-psat)
            if phi==0.:
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_=h_a
            elif round(phi,2)==1.:
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_w=state(["T","x"],[T,1.],"water",Eh)["h"]-h_w0
                h_=h_a+X*h_w
            else:
                p_w=phi*psat      
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_w=state(["T","p"],[T,p_w],"water",Eh)["h"]-h_w0
                h_=h_a+X*h_w
            return h_-h
        if phi>1.:
            print("State is oversaturated")
            T=nan
            X=nan
        else:
            T=brentq(help2,.1,60.)
            psat=state(["T","x"],[T,0.],"water",Eh)["p"]
            X=.622*psat/(p/phi-psat)
            
            
    elif Var[0]=="h*" and Var[1]=="phi":
        phi=In[1]
        h=In[0]
        
        def help2(T_):
            T=T_
            psat=state(["T","x"],[T,0.],"water",Eh)["p"]
            X=.622*psat/(p/phi-psat)
            if phi==0.:
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_=h_a
            elif round(phi,2)==1.:
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_w=state(["T","x"],[T,1.],"water",Eh)["h"]-h_w0
                h_=h_a+X*h_w
            else:
                p_w=phi*psat      
                h_a=state(["T","p"],[T,p],"air",Eh)["h"]-h_a0
                h_w=state(["T","p"],[T,p_w],"water",Eh)["h"]-h_w0
                h_=h_a+X*h_w
            return h_-h
        if phi>1.:
            print("State is oversaturated")
            T=nan
            X=nan
        else:
            T=brentq(help2,.1,60.)
            psat=state(["T","x"],[T,0.],"water",Eh)["p"]
            X=.622*psat/(p/phi-psat)
    
    ## Calculation of specific volume
    psat=state(["T","x"],[T,0.],"water",Eh)["p"]
    p_water=phi*psat
    p_air=1.-p_water

    v_air=state(["T","p"],[T,p_air],"air",Eh)["v"]
    v=v_air

    state_m=pd.Series([T,X,phi,h,v],index=index_m)
    return state_m


def cp_moist_air(T, phi=0.6, p_bar=1.0):
    """
    Specific heat of moist air per unit mass of dry air [J/(kg_da·K)].
    T    : temperature in °C (scalar or array)
    phi  : relative humidity (0–1), default 0.6
    p_bar: pressure in bar, default 1.0
    Uses CoolProp HumidAir backend (HAPropsSI).
    """
    import numpy as np
    T_arr = np.atleast_1d(np.asarray(T, dtype=float))
    cp_arr = np.array([
        CP.HAPropsSI("C", "T", t + dTk, "P", p_bar * 1e5, "R", phi)
        for t in T_arr
    ])
    return cp_arr if cp_arr.size > 1 else float(cp_arr[0])


def cp_moist_poly(phi=0.6, p_bar=1.0, T_min=-20.0, T_max=40.0, deg=2):
    """
    Polynomial fit of cp_moist_air over [T_min, T_max] (°C).
    Returns numpy.poly1d: call result like  cp_poly(T_in_degC).
    Units: J/(kg_da·K)
    """
    import numpy as np
    T_fit = np.linspace(T_min, T_max, 200)
    cp_fit = cp_moist_air(T_fit, phi=phi, p_bar=p_bar)
    coeffs = np.polyfit(T_fit, cp_fit, deg)
    return np.poly1d(coeffs)
