"""
To Do:
   1. Option to specify filename for output .ics file
   2. 
"""
import time
import urllib2
from bs4 import BeautifulSoup as BS
import re
from collections import OrderedDict

# ##############################
# Utils
# ##############################
# URL of WebEvent CGI interface
cgi_url = 'http://calendar.ufl.edu/cgi-bin/webevent/webevent.cgi'
# Current UTC Time
time_struct = time.gmtime()
utc_mmdd = '{0:02d}{1:02d}'.format(time_struct.tm_mon, time_struct.tm_mday)
utc_hhmmss = '{0:02d}{1:02d}{2:02d}'.format(time_struct.tm_hour, time_struct.tm_min, time_struct.tm_sec)
current_year = str(time_struct.tm_year)
# time in ical string
ical_time_string = current_year + utc_mmdd +'T'+ utc_hhmmss +'Z'
# Timezone (standard and DST)
std_tz_hour = int(time.timezone / 3600.)
dst_tz_hour = int(time.altzone / 3600.)

# ##############################################
# UTILS -- Convert vcal event to ical event
# ##############################################
# SubStrings to Kill from each .vcs file string
bad_vcal_substring_list = ['BEGIN: VCALENDAR\nVERSION: 1.0\n', '\nEND: VCALENDAR\n']
# ical format required keys and defaults
ical_defaults = OrderedDict()
ical_defaults['BEGIN'] = 'VEVENT'
ical_defaults['DTSTART'] = ''
ical_defaults['DTEND'] = ''
ical_defaults['DTSTAMP'] = ical_time_string
ical_defaults['UID'] = ''
ical_defaults['CREATED'] = ical_time_string
ical_defaults['DESCRIPTION'] = ''
ical_defaults['LAST-MODIFIED'] = ical_time_string
ical_defaults['LOCATION'] = ''
ical_defaults['SEQUENCE'] = '0'
ical_defaults['STATUS'] = 'CONFIRMED'
ical_defaults['SUMMARY'] = ''
ical_defaults['TRANSP'] = 'OPAQUE'
ical_defaults['END'] = 'VEVENT'

#
def convert_vcal_to_ical(vcal_string):

    ical_dict = {}
    ical_string_list = []

    # ---------------------
    # Initial Cleaning
    # ---------------------
    # Remove Bad vcal substrings
    for bad_substring in bad_vcal_substring_list:
        vcal_string = vcal_string.replace(bad_substring, '')
    # 'CLASS:' lines
    class_line_list = re.findall('(CLASS\:.*\n)', vcal_string)
    for class_line in class_line_list:
        vcal_string = vcal_string.replace(class_line, '')

    # -----------------------------
    # Convert vcal string to dict
    # -----------------------------
    vcal_data_dict = {}
    # Step 1: List of lines
    vcal_line_list = vcal_string.split('\n')
    # Step 2: Parse Each line for Key, Data
    for vcal_line_string in vcal_line_list:
        # Parse out Key, Data
        vcal_line_key_raw = re.findall('([A-Z\-]*: )', vcal_line_string)[0]
        vcal_line_key = vcal_line_key_raw.replace(': ','')
        vcal_line_data = vcal_line_string.replace(vcal_line_key_raw, '')
        # Step 3: Put into dict
        vcal_data_dict[vcal_line_key] = vcal_line_data

    # ------------------------------
    # Fix the Date of All-Day Events
    # ------------------------------
    if vcal_data_dict['DTSTART'] == vcal_data_dict['DTEND']:

        # *** UGLY HACK ***
        # Check if event time consistent with midnight 
        # (if so, change to all-day event)
        # (if not, leave time as-is -- will be added later)
        # *****************
        event_hour_str = vcal_data_dict['DTSTART'].split('T')[-1][0:2]
        event_hour_int = int(event_hour_str)
        if event_hour_int == std_tz_hour or event_hour_int == dst_tz_hour:

            # Event Time is Consistent with Midnight
            # (Make event an All-Day Event)
            # -----------------------------
            # Parse out start date
            start_date_str = vcal_data_dict['DTSTART'].split('T')[0]
            start_date_int = int(start_date_str)
            # Increment to get end date
            end_date_int = start_date_int + 1
            
            # Make Final DTSTART and DTEND entries
            ical_dict['DTSTART'] = ';VALUE=DATE:'+ start_date_str
            ical_dict['DTEND'] = ';VALUE=DATE:'+ str(end_date_int)

    # ------------------------------
    # Build ical-Format String
    # ------------------------------
    for ical_key in ical_defaults:

        # Part 1: Get data values from ical and vcal dictionaries
        # -----------------------------------------------------
        # Check if key has already been added to ical_dict
        # (for handling special cases like the start/end dates)
        if ical_key not in ical_dict:
            
            # Check for Value in vcal Dict
            if ical_key not in vcal_data_dict:
                # No vcal Value for this key -- Add default from ical_default
                ical_dict[ical_key] = ':'+ ical_defaults[ical_key]
            else:
                # There is a vcal value for this key  -- Check length of string
                if len(vcal_data_dict[ical_key]) == 0:
                    # If vcal data string is empty -- use default
                    ical_dict[ical_key] = ':'+ ical_defaults[ical_key]
                else:
                    # If vcal string is non-empty -- use vcal string
                    ical_dict[ical_key] = ':'+ vcal_data_dict[ical_key]
                    
        # Part 2: Make Dictionary Entries into Strings, Append to list
        # -----------------------------------------------------------
        ical_string_list.append(ical_key + ical_dict[ical_key])

    # Part 3: Join List with newlines, return
    # ---------------------------------------
    ical_data_string = '\n'.join(ical_string_list)
    return ical_data_string

# ##############################
# Downloading Calendar
# ##############################
def download_calendar(year=current_year, cal_type='academic', debug=False):
#def download_calendar(**kwargs):
    """
    Deals with details of calendar CGI interface
    kwargs -- cal_type, year
    """
    
    # Error Checking
    # ---------------
    # The year must be a numeric type convertable to integer
    try: year = int(year)
    except: raise TypeError('Year must be a number')
    # Calendar Types are restricted
    assert 'academic' in cal_type or 'athletic' in cal_type

    # Construct URL
    # --------------
    cal_dict = {'academic':'cal3', 'athletic':'cal4'}
    cal_url = '{0:s}?cmd=listyear&cal={1:s}&y={2:d}'.format(cgi_url, cal_dict[cal_type], year)

    # Get HTML from cal page
    # -------------------------
    cal_socket = urllib2.urlopen(cal_url)
    cal_page_html = cal_socket.read()

    return cal_page_html


# ##############################
# Parsing HTML
# ##############################
def parse_calendar(cal_page_html=None):
    """
    Deals with details of internal calendar-page HTML formatting
    Returns list of calendar event IDs
    """
    # Make sure we actually got something
    assert cal_page_html is not None

    # -----------------------------------
    # Parse Out Event IDs
    # -----------------------------------
    # List for eventIDs parsed from calendar page html
    event_id_list = []
    # Parse with BeautifulSoup
    cal_page_soup = BS(cal_page_html)
    # list of tags with listeventtitle class -- eventIDs are embedded in some of these
    eventtitle_tag_list = cal_page_soup.find_all('div', class_='listeventtitle')

    # Loop Through listeventtitle tags
    for eventtitle_ind,eventtitle_tag in enumerate(eventtitle_tag_list):

        # This gets the eventtitle <a> tag which has the eventID embedded in the HREF
        event_link_tag = eventtitle_tag.find('a')

        # Skip over dummy eventtitle tags
        if event_link_tag is None: 
            continue
        
        # Get the href string
        event_link_string = event_link_tag['href']
        # Parse out the eventID 
        raw_event_id_string = re.findall('(&id=\d{6}&)', event_link_string)[0]
        event_id_string = raw_event_id_string.replace('&','').split('=')[-1]

        # Add the eventID to the list
        event_id_list.append(event_id_string)

    return event_id_list

# ##############################
# Downloading Event .vcs Data
# ##############################
def download_event_data(**kwargs):
    """
    Deals with details of data export from the WebEvent API
    """
    # -----------------
    # Get List of EventIDs on Desired Calendar
    # -----------------
    # Download Calendar HTML
    cal_page_html = download_calendar(**kwargs)
    # Parse Calendar HTML for list of eventIDs
    event_id_list = parse_calendar(cal_page_html=cal_page_html)

    # -----------------
    # Get Event Data
    # -----------------
    event_data_list = []
    # This is how to get event data from the WebEvent API using eventIDs
    base_url = '{0:s}?cmd=e2vcal'.format(cgi_url)

    # Loop over eventIDs
    for event_ind,event_id_string in enumerate(event_id_list):
        # # **************************************
        # if event_ind>2: break
        # # **************************************
        # Construct URL of vcs data
        event_data_url = '{0:s}&id={1:s}'.format(base_url, event_id_string)
        # Download Event Data
        event_data_socket = urllib2.urlopen(event_data_url)
        event_data = event_data_socket.read()

        # Append to list of event data strings
        event_data_list.append(event_data)

    return event_data_list

# ##############################
# Making ical file
# ##############################
def make_ical(**kwargs):

    # ----------------------
    # Get List of Event Data
    # ----------------------
    event_data_list = download_event_data(**kwargs)

    # =====================================
    # Construct valid(-ish) iCal File
    # =====================================
    cleaned_event_data_list = []

    # ----------------------------
    # Clean Up Event Data Entries
    # ----------------------------
    # Loop through event data entries
    for event_data_string in event_data_list:
        # Send to conversion/cleaning function
        ical_data_string = convert_vcal_to_ical(event_data_string)
        # Append to List of cleaned event entries
        cleaned_event_data_list.append(ical_data_string)

    # ----------------------------
    # Add Header and Footer
    # ----------------------------
    # Header
    ical_header_list = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
                        'X-WR-CALNAME:Group Meetings', 'X-WR-TIMEZONE:America/New_York', 'X-WR-CALDESC:',
                        'BEGIN:VTIMEZONE', 'TZID:America/New_York', 'X-LIC-LOCATION:America/New_York',
                        'BEGIN:DAYLIGHT', 'TZOFFSETFROM:-0500', 'TZOFFSETTO:-0400', 'TZNAME:EDT',
                        'DTSTART:19700308T020000', 'RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU', 'END:DAYLIGHT',
                        'BEGIN:STANDARD', 'TZOFFSETFROM:-0400', 'TZOFFSETTO:-0500', 'TZNAME:EST',
                        'DTSTART:19701101T020000', 'RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU', 'END:STANDARD',
                        'END:VTIMEZONE']
    ical_header = '\n'.join(ical_header_list)
    # Footer
    ical_footer = 'END:VCALENDAR\n'

    # Join Into ical file
    # -------------------
    ical_file_string = ''
    ical_file_string += ical_header
    ical_file_string += '\n'
    ical_file_string += '\n'.join(cleaned_event_data_list)
    ical_file_string += '\n'
    ical_file_string += ical_footer

    # ------------
    # Return
    # ------------
    return ical_file_string

# ##############################
# Command-Line Invocation
# ##############################
if __name__ == '__main__':
    import argparse

    # Command-Line Argument Parsing
    parser = argparse.ArgumentParser(description='Forcibly exporting the University of Florida WebEvent calendar to an iCalendar format file.')
    parser.add_argument('--cal', default='academic', type=str,
                        help="Which calendar to rip. Must be either 'academic' or 'athletic'.",
                        choices=['academic','athletic'], dest='cal_type')
    parser.add_argument('--year', default=2014, type=int,
                        help="Calendar year to rip. Must be convertable to int-type.",
                        dest='year')
    args = parser.parse_args()

    print args
    print fake

    # Call cal-ripper
    ical_file_string = make_ical(year=year, cal_type=cal_type) 

    # Write to File
    # ----------------------------
    output_filename = '{0:s}_{1:s}.ics'.format(cal_type, str(year))
    # Write
    with open(output_filename, 'w') as f:
        f.write(ical_file_string)
    print 'Wrote: '+ output_filename

