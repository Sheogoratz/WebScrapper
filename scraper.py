import requests
import colorama
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import sys
from threading import Thread
import time
import argparse
from datetime import datetime


colorama.init()     #Color support
GREEN = colorama.Fore.GREEN #For subdomains links (safe links)
RED = colorama.Fore.RED #For errors or external links in tor (unsafe links)
BLUE = colorama.Fore.BLUE #for external clear web links
RESET = colorama.Fore.RESET
YELLOW = colorama.Fore.YELLOW #just to give some visibility for some stuff

Tor = True
Darknet = False

CheckNaughty = False
Blacklist = ('porn', 'PORN', 'CP') #I didn't have much idea of what to ban, but banning porn because it is useless and child abuse because it is horrible seemed the minimum
keepcopies = False

def tor():
    ip = requests.get ("http://ifconfig.me")            #lookup current public ip
    global session                                          
    session = requests.session()                            #initialises session, tor must be running
    session.proxies = {}
    session.proxies['http'] = 'socks5h://localhost:9050'    #if tor runs on non default port, change the localhost proxy
    session.proxies['https'] = 'socks5h://localhost:9050'
    newip = session.get("http://ifconfig.me")               #looks new exit node ip

    if ip == newip :
        sys.exit(f"{RED}* Tor not running correctly, exiting{RESET}")
    else:
        print(f"* Tor is configured and working, old ip : {YELLOW}{ip.text}{RESET}, new ip : {YELLOW}{newip.text}{RESET}")  #display the user the ip change with tor


def urlfinder (domain, url, internalurl, externalurl, otherlink, newlinks):
    #print (domain)
    page = session.get(url, timeout=10 )
    soup = BeautifulSoup(page.content, 'html.parser')
    urls = soup.find_all('a')
    for a in urls:
        href = a.attrs.get("href") #href is the code where the url is stored
        if href == "" or href is None:
            # href empty tag
            continue
        href = urljoin(url, href)

        if CheckNaughty == True:  #If blacklist is in place, will check if the blacklisted keywords are in the link info, its not 100% fool proof but its a good, start
            Naughty = False
            for z in Blacklist: #I wanted to put it in a function, but i wanted to continue to keep working for the for a in url
                if z in href:
                    Naughty = True
            if Naughty == True:
                print (f"* New blacklisted link discovered in {YELLOW}{domain}{RESET}, subjet = {RED}{a.term}{RESET}")
                continue
            
        #parsed_href = urlparse(href)    #legacy code, ill leave it here for now
        #href = parsed_href.scheme + "://" + parsed_href.netloc + parsed_href.path #remove https and get information
        
        if domain == href.split("//")[-1].split("/")[0]:
            if href in internalurl: #check if url is already discovered on the domain, if not add it to the list of url on the domain and url to scrap
                continue
            internalurl.add(href)
            newlinks.add(href)
            print (f"* New internal link discovered : {GREEN}{href}{RESET}  in {YELLOW}{domain}{RESET}", a.text)
            continue
        else:
            if Darknet == True:    #A bit the same as before, just that we need to make a case disjunction between links to follow and links not to follow depending if the darknet option is enabled. its a bit ugly, but it works fine without bugs
                if ".onion" in href:            
                    if href not in externalurl:
                        print (f"* New external link discovered : {RED}{href}{RESET} in {YELLOW}{domain}{RESET}", a.text)
                        externalurl.add(href)
                        continue
        
                if ".onion" not in href:
                    if href in otherlink:
                        continue
                    else:
                        print (f"* New clearweb link discovered : {BLUE}{href}{RESET} in {YELLOW}{domain}{RESET}", a.text)
                        otherlink.add(href)
                        continue

            if Darknet == False:
                if ".onion" in href:
                    if href not in otherlink:
                        print (f"* New darknet link discovered : {RED}{href}{RESET} in {YELLOW}{domain}{RESET}", a.text)
                        otherlink.add(href)
                        continue
                if ".onion" not in href:
                    if href not in externalurl:
                        print (f"* New external link discovered : {BLUE}{href}{RESET} in {YELLOW}{domain}{RESET}", a.text)
                        externalurl.add(href)
    scrapedurls.add(url) #add the url to the list of scrapped urls, so it doesnt get scrapped twice
    if keepcopies == True:
        contentdb[url] = page.text #saves the content in the dictionary, can be usefull if we want a search function after
    return

def websitescraper(domain, links, internalurl, externalurl, otherlink, newlinks): #this one is the one that will scrap all internal links from a domain, and keep track of all external links
    #print (links)
    Threads = []
    newlinks = set()
    for url in links:
        newlinks = set()
        if url in scrapedurls: #Im a bit lost with all the recusion at the point, so implementing double failsafes is not nessecarly a bad idea
            continue
        if ".onion" not in url:
            if Darknet == True:
                continue
        if ".onion" in url:
            if Darknet == False:
                continue
        try:
            print (f"\n* Scrapping {url}")
            process = Thread(target=urlfinder(domain, url, internalurl, externalurl, otherlink, newlinks))  #Why threads over multiproccessing ? its easier to implement, and it keeps the output coherent, anyways the slowest part is the network, so it doesnt change much
            process.start()
            Threads.append(process)
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError): #A connection timeout is required, otherwise the code can hang for ages
            e = sys.exc_info()[0]
            print (f"\n{RED}* Failed scrapping {url} with error code {e}{RESET}")
            timeouts.add(url)
            continue
    
    for process in Threads:
        process.join() #We wait for all the threads to finish, 
    #print ("\n * All links scraped, scraping internal links \n")  #more legacy code
    if len(newlinks) == 0: #When all internal links have been scrapped, the recursion stops, and the thread will end
        #fullyscrappeddomain = [domain, internalurl, externalurl, clearweburl]
        if Darknet == True:
            print (f"\n* Finished scrapping {YELLOW}{domain}{RESET}, with {GREEN}{len(internalurl)}{RESET} pages, links to {RED}{len(externalurl)}{RESET} onion services and {BLUE}{len(otherlink)}{RESET} non onion services \n")  #Quite ugly again, but it does the job
        if Darknet == False:
            print (f"\n* Finished scrapping {YELLOW}{domain}{RESET}, with {GREEN}{len(internalurl)}{RESET} pages, links to {BLUE}{len(externalurl)}{RESET} websites\n")
        #print (fullyscrappeddomain)
        return


    links.clear()
    for i in newlinks:
        links.add(i)
    #print (links)
    websitescraper(domain, links, internalurl, externalurl, otherlink, newlinks)


def stopspyder(endstate):
    if keepcopies == True:
        for x in contentdb:
            name = x.replace('https://','')
            name = name.replace('http://','')
            name = name.replace('/','_')
            timenow = datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
            with open(f"{name}_{timenow}","w") as logfile:
                print(contentdb[x], file=logfile)
                print (f"* Saved {YELLOW}{x}{RESET} to {BLUE}{timenow}{RESET}")

    sys.exit(f"\n* Webscrapper stopped with exit code : {endstate}")  
    #print (scrapedurls)
    #Here im maybe gonna add the display function and or the search function, stay updated folks


def mainscraper(websites, i): #the mainscrapper in the loop that scraps entire domains
    global newwebsites
    newwebsites = set()
    if len(websites) == 0:
        endstate = f"We have achieved the end of the net after {i} iterations, how is that even possible ?" #If the starting website has very few links it can actually happen but is very unlikely
        stopspyder(endstate)
    start = time.perf_counter()
    threads = []
    todo = websites
    for a in todo:
        domain=a.split("//")[-1].split("/")[0]
        links = set()
        links.add(a)
        internalurl = set()
        externalurl = set()
        clearweburl = set()
        newlinks = set()
        process = Thread(target=websitescraper(domain, links, internalurl, externalurl, clearweburl, newlinks)) #Once more threads in loops for speeed
        process.start
        threads.append(process)

    for process in threads:
        if 'initial' in str(process): #if there is only the initial thread, i get runtimes errors
            continue
        process.join()

    stop = time.perf_counter()
    print (f"Scrapped {len(websites)} in {stop - start} seconds") #Because sometimes it can be nice to monitor the speed of the programm
    #print (externalurl)

    if i == limit: #count the depth of external recursion
        endstate = f"Recursion limit of {limit} attained"
        stopspyder(endstate)
    i += 1
    try :
        newwebsites = externalurl    
        mainscraper(newwebsites, i)
    except (UnboundLocalError):
        endstate = f"Recursion limit of {limit} attained"
        stopspyder(endstate)

def spyder(startingurl):
    if Tor == True:
        try:
            tor()
        except:
            sys.exit(f"\n{RED}* Failed connecting to tor network with error code {sys.exc_info()[0]}\n{RESET}")
    if Tor == False:
        global session                                          
        session = requests.session()

    global scrapedurls, timeouts, contentdb
    scrapedurls = set()
    timeouts = set()
    contentdb = {}
    websites = set()
    websites.add(startingurl)
    try:
        i = 0
        mainscraper(websites, i)
    except (KeyboardInterrupt):
        endstate = "User interuption"
        stopspyder(endstate)

def main():
    parser = argparse.ArgumentParser()  #Argument parser
    parser.add_argument("-n","--no_tor", action="store_true", default=False, help="Disables tor, has no effect if used with -o")
    parser.add_argument("-o","--onion", action="store_true", default=False, help="Set the crawler to explore onion domains, will set default url to the hidden wiki http://torlinkbgs6aabns.onion/ ")
    parser.add_argument("-b", "--blacklist_disable", action="store_true", default=False, help="Disables the blacklist, NOT RECOMMENDED")
    parser.add_argument("-s","--searcheable", action="store_true", default=False, help="Keep scrapped webpages in memory to post process them")
    parser.add_argument("-r","--recursion", type=int, default=0, help="Number of times the webcrawler will follow external links recursivly")
    parser.add_argument("-u","--url", type=str, default="https://en.wikipedia.org/wiki/Main_Page", help="Default page to crawl from. Defaults to https://en.wikipedia.org/wiki/Main_Page")
    args=parser.parse_args()

    global Tor, Darknet, limit

    startingurl = args.url

    limit = args.recursion

    if args.no_tor == True:
        Tor = False
        Darknet = False

    if args.onion == True:
        Darknet = True
        Tor = True
        if args.url == "https://en.wikipedia.org/wiki/Main_Page":
            startingurl = "http://torlinkbgs6aabns.onion/"

    if args.searcheable == True:
        global keepcopies
        keepcopies = True

    if args.blacklist_disable == True:
        x = True
        while x == True:
            print(f"{RED}* Are you sure you want to disable the blacklist ? You could stumble upon horrible stuff.{RESET}")
            consent=input("* Type YES to continue, NO if you want to stay safe :\n")
            if consent == 'YES':
                global CheckNaughty
                CheckNaughty = False
                x = False
            if consent == 'NO':
                x = False
        

    spyder(startingurl)

if __name__ == "__main__":
    main()   
