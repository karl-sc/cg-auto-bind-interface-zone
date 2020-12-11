# cg-auto-bind-interface-zone
Autobinds cloudgenix interfaces to zones based on simple text matching

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
