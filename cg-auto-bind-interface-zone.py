#!/usr/bin/env python
PROGRAM_NAME = "cg-auto-bind-interface-zone.py"
PROGRAM_DESCRIPTION = """
CloudGenix script to find all instances of an interface based on regex and if it is not mapped to a security zone, map it
---------------------------------------
This script finds all sites with spoke/branch elements and searches their ZBFW zone mappings.
Any zones found matching the input ZoneName parameter which are not bound to anything will be bound
to interfaces that start with the interface-match parameter. 


This script is most useful for those who are using the Prisma Access or zScaler cloudblade with cloudgenix and want to 
automatically assigned cloudblade managed interfaces to a zone for use with the ZBFW

Examples:
python3 cg-auto-bind-interface-zone.py --zonename zscaler --interface-match sl-zscaler
python3 cg-auto-bind-interface-zone.py --zonename prisma --interface-match AUTO-PRISMA_IPSEC-Tunnel


"""
from cloudgenix import API, jd
import os
import sys
import argparse

from fuzzywuzzy import fuzz, process

CLIARGS = {}
cgx_session = API()              #Instantiate a new CG API Session for AUTH

def parse_arguments():
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=PROGRAM_DESCRIPTION
            )
    parser.add_argument('--token', '-t', metavar='"MYTOKEN"', type=str, 
                    help='specify an authtoken to use for CloudGenix authentication')
    parser.add_argument('--authtokenfile', '-f', metavar='"MYTOKENFILE.TXT"', type=str, 
                    help='a file containing the authtoken')
    parser.add_argument('--zonename', '-z', metavar='zonename', type=str, 
                    help='the zone name to look use', required=True)
    parser.add_argument('--interface-match', '-i', metavar='interface-match', type=str, 
                    help='the prefix of the interface name to match for', required=True)
    args = parser.parse_args()
    CLIARGS.update(vars(args)) ##ASSIGN ARGUMENTS to our DICT
    print(CLIARGS)

def authenticate():
    print("AUTHENTICATING...")
    user_email = None
    user_password = None
    
    ##First attempt to use an AuthTOKEN if defined
    if CLIARGS['token']:                    #Check if AuthToken is in the CLI ARG
        CLOUDGENIX_AUTH_TOKEN = CLIARGS['token']
        print("    ","Authenticating using Auth-Token in from CLI ARGS")
    elif CLIARGS['authtokenfile']:          #Next: Check if an AuthToken file is used
        tokenfile = open(CLIARGS['authtokenfile'])
        CLOUDGENIX_AUTH_TOKEN = tokenfile.read().strip()
        print("    ","Authenticating using Auth-token from file",CLIARGS['authtokenfile'])
    elif "X_AUTH_TOKEN" in os.environ:              #Next: Check if an AuthToken is defined in the OS as X_AUTH_TOKEN
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('X_AUTH_TOKEN')
        print("    ","Authenticating using environment variable X_AUTH_TOKEN")
    elif "AUTH_TOKEN" in os.environ:                #Next: Check if an AuthToken is defined in the OS as AUTH_TOKEN
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('AUTH_TOKEN')
        print("    ","Authenticating using environment variable AUTH_TOKEN")
    else:                                           #Next: If we are not using an AUTH TOKEN, set it to NULL        
        CLOUDGENIX_AUTH_TOKEN = None
        print("    ","Authenticating using interactive login")
    ##ATTEMPT AUTHENTICATION
    if CLOUDGENIX_AUTH_TOKEN:
        cgx_session.interactive.use_token(CLOUDGENIX_AUTH_TOKEN)
        if cgx_session.tenant_id is None:
            print("    ","ERROR: AUTH_TOKEN login failure, please check token.")
            sys.exit()
    else:
        while cgx_session.tenant_id is None:
            cgx_session.interactive.login(user_email, user_password)
            # clear after one failed login, force relogin.
            if not cgx_session.tenant_id:
                user_email = None
                user_password = None            
    print("    ","SUCCESS: Authentication Complete")
    return cgx_session

def bind_interface_to_zone(site, element, zone_id, interface):
    site_id = site['id']
    element_id = element['id']
    interface_id = interface['id']
    mapping_exists = False
    element_zone_mappings = sdk.get.elementsecurityzones(site_id, element_id).cgx_content.get("items")
    for mapping in element_zone_mappings:
        if mapping['zone_id'] == zone_id:
            if mapping['interface_ids'] is not None:
                for mapped_interface_id in mapping['interface_ids']:
                    if mapped_interface_id == interface_id:
                        mapping_exists = True
                        print("IGNORING: mapping exists for",site['name'],"element",element['name'])
                        return False
            else:
                mapping['interface_ids'] = []
            if mapping_exists == False: ###Zone exists but needs to be modified. We should abort
                print("ABORTING: Zone already has interfaces mapped. Aborting",site['name'],"element",element['name'])
                return True
    ##ZONE DOESNT EXIST AS MAPPED AND NEEDS TO BE ADDED
    post_data = {"zone_id":str(zone_id),"lannetwork_ids":[],"interface_ids":[str(interface_id)],"wanoverlay_ids":[],"waninterface_ids":[]}
    result = sdk.post.elementsecurityzones(site_id, element_id, post_data)
    if result.cgx_status:
        print("CREATING: Added new mapping for interface to zone for site",site['name'],"element",element['name'])
    else:
        print("FAILED CREATING: Added new mapping for interface to zone for site",site['name'],"element",element['name'])
    return True
    
def go(sdk, zone_id, starts_with_match):
    
    ####CODE GOES BELOW HERE#########
    
    all_site_list = sdk.get.sites().cgx_content.get("items", None)
    branch_sites = []
    for site in all_site_list:
        if site['element_cluster_role'] == 'SPOKE':
            branch_sites.append(site)
    
    element_list = sdk.get.elements().cgx_content.get("items",None)

    for site in branch_sites:
        for element in element_list:
            if site['id'] == element['site_id']: ##Found a site with an element
                interface_list = []
                interface_list = sdk.get.interfaces(site['id'],element['id']).cgx_content.get("items",None)
                for interface in interface_list:
                    if str(interface['name']).startswith(starts_with_match):
                        bind_interface_to_zone(site, element, zone_id, interface)

    ####CODE GOES ABOVE HERE#########

def match_zone(sdk, query):
    zone_list = sdk.get.securityzones().cgx_content.get("items", None)
    zone_name = []
    zone_id = []
    for zone in zone_list:
        zone_name.append(zone['name'])
    choice, percent = process.extractOne(query, zone_name)
    if percent > 80:
        for zone in zone_list:
            if zone['name'] == choice:
                print("Found zone match as",zone['name'])
                return zone['id']
    else:
        print("No good matches for zone query found")
        return False

def logout():
    print("Logging out")
    cgx_session.get.logout()

if __name__ == "__main__":
    parse_arguments()
    sdk = authenticate()
    if sdk:
        zone_id = match_zone(sdk, CLIARGS['zonename'])
        go(sdk, zone_id, CLIARGS['interface_match'])
        logout()
