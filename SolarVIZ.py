# SolarVIZ Server 
# v0.0  (19.07.2019)
# v0.1  (23.07.2019)
# v0.2  (01.08.2019)
# v0.3  (06.08.2019)
# v0.4  (08.08.2019)
# v0.5  (11.08.2019)
# v0.9  (29.08.2019)
# v0.91 (03.01.2020)
# v0.92 (04.01.2020)
# (c) Rami Saarivuori 2020

VIZversion = "0.92"
polku = '//home//pi//SolarVIZ//' # absoluuttinen polku tarvitaan, jotta ohjelma toimii crontabin kanssa oikein
arch = '//media//pi//KINGSTON//' # arkiston polku
archiveDate = ''
screenState = 0


try:
	import schedule, multiprocessing, time, socket, os, epd2in7b, logging
	from urllib import request as rq
	from datetime import date
	from PIL import Image,ImageDraw,ImageFont
	from gpiozero import Button
except Exception:
	logging.error("Kirjastojen tuonti epäonnistui, lopetetaan.")
	exit(-1)

class PowerData:
	def __init__(self):
		self.PAC = 0
		self.PAC_unit = "W"
		self.day_energy = 0
		self.year_energy = 0
		self.total_energy = 0
		self.energy_unit = "Wh"
		self.InverterStatus = 0

def StartUp(): # käynnistys
	logging.info("Initializing...")
	try:
		name = polku + "config.cfg"
		tdsto = open(name, "r", encoding="utf-8")
		startState = 0 # tiedosto löytyi, eli ei ensimmäinen kerta
		logging.info("Config found")
	except FileNotFoundError: #tiedostoa ei löydetty
		startState = 1
		logging.info("Config not found")
		pass
		
	if startState == 1: #koska tiedostoa ei löydetty, kysytään ohjelman toiminnan kannalta oleelliset tiedot "config" tiedostoon
		info = []
		print("Tervetuloa käyttämään SolarVIZ -ohjelmistoa, jonka tarkoituksena on kerätä, arkistoida ja visualisoida aurinkosähköjärjestelmien tuottamaa dataa. Ohjelma on tällä hetkellä yhteensopiva FRONIUS invertterien kanssa, jotka tukevat FRONIUS Solar API:n versiota 1.")
		print("Aloitetaan käyttöönotto.")
		nimi = input("Anna järjestelmällesi nimi: ")
		logging.info("System name: %s", nimi)
		time.sleep(1)
		MAX_P = input("Anna järjestelmän maksimituotto (W): ") #kuvaajia varten
		logging.info("System max: %s", MAX_P)
		time.sleep(1)
		InverterIP = input("Anna invertterin IP-osoite (muodossa 123.456.789.012): ")#tärkein asia toiminnan kannalta, ilman tätä ohjelma ei pysty toimimaan
		InverterIP.strip("\n")
		logging.info("Inverter IP: %s", InverterIP)
		
		#Tähän vielä jotain IP-osoitteen muodollisuuden tarkistusta?
		#Ja että MAX_P on luku?
		
		info.append(nimi)
		info.append(MAX_P)
		info.append(InverterIP)
		
		try:
			file = open(name, "w", encoding="utf-8")
		except Exception:
			logging.error("Config file writing failed.")
			exit(-1)
		
		file.write("SolarVIZ, V"+VIZversion+" configuration for '"+nimi+"'\n") #kirjoitetaan asetustiedosto
		for i in info:
			file.write(i+"\n")
			
		file.close()
		logging.info("Config saved, initialization succesfull")
		return info
		
	elif startState == 0:
		info = []
		rivi = tdsto.readline()
		while True:
			rivi = tdsto.readline()
			if len(rivi) == 0:
				break
			
			info.append(rivi[:-1])
		tdsto.close()
		logging.info("Initialization successfull.")
		return info

def GetInverterData(info): # haetaan data rajapinnan kautta invertteriltä
	logging.info("Muodostetaan yhteys invertteriin...")
	try:
		solarData = rq.urlopen("http://"+info[2]+"/solar_api/v1/GetInverterRealtimeData.cgi?Scope=System")
	except Exception: #invertteriin ei saatu yhteyttä
		logging.error("Virhe muodostettaessa yhteyttä invertteriin.")
		ReturnedData = -1
		return ReturnedData
		
	ReturnedData = solarData.read().decode('utf-8')
	splitData = ReturnedData.split("\n")
	i = 0
	cleanedData = []
	for item in splitData:
		temp = splitData[i].strip(" ")
		cleanedData.append(temp)
		i = i+1
		
	sortedData = PowerData() #luodaan uusi luokkainstanssi uudelle datalle ja lisätään data
	sortedData.day_energy = cleanedData[6][6:]
	sortedData.PAC = cleanedData[12][6:]
	sortedData.total_energy = cleanedData[18][6:]
	sortedData.year_energy = cleanedData[24][6:]
	sortedData.InverterStatus = cleanedData[35][9:10]
	logging.info("Data järjestelty.")
	return sortedData

def tempSaveData(solarData): #väliaikainen tallennus tekstitiedostoon jotta data voidaan arkistoida päivän päätteeksi
	kello = time.strftime("%H-%M-%S")
	paiva = date.today().strftime("%Y-%m-%d")
	name = polku+paiva+".txt"
	yn = "n"
	name2 = paiva+".txt"
	files = os.listdir(polku)
	for a in files:
		if a == name2:
			yn = "y"
	
	try:
		if int(kello.split('-')[0]) == 0 and int(kello.split('-')[1]) <= 4:
			file = open(name, "w", encoding='utf-8')
			tallennus = kello+":"+solarData.PAC+":"+solarData.day_energy+"\n"
			file.write(tallennus)
			file.close()
			logging.info("Tallennus onnistui. (Klo 00)")
			
		elif int(kello.split('-')[0]) >= 23 and int(kello.split('-')[1]) >= 50:
			file = open(name, "a", encoding='utf-8')
			tallennus = kello+":"+solarData.PAC+":"+solarData.day_energy+":"+solarData.year_energy+":"+solarData.total_energy+"\n"
			file.write(tallennus)
			file.close()
			logging.info("Tallennus onnistui. Klo 23")
			
		elif yn == "y":
			file = open(name, "a", encoding='utf-8')
			tallennus = kello+":"+solarData.PAC+":"+solarData.day_energy+"\n"
			file.write(tallennus)
			file.close()
			logging.info("Tallennus onnistui. (perus)")
			
		else:
			file = open(name, "w", encoding='utf-8')
			tallennus = kello+":"+solarData.PAC+":"+solarData.day_energy+"\n"
			file.write(tallennus)
			file.close()
			logging.info("Tallennus onnistui. (uusi tiedosto)")
	except Exception:
		logging.error("Tallennus epäonnistui.")
		return

def archive(): #pitempi aikainen tallennus taulukkoon (päivän lopuksi)
	logging.info("Aloitetaan arkistointi.")
	aika = date.today().strftime("%Y-%m-%d")
	aika2 = aika+"\n"
	aika3 = aika
	tempfile = polku+aika+".txt"
	files = os.listdir(arch)
	yn = "n"

	if archiveDate == aika:
		logging.info("Perutetaan arkistointi, arkistointi on jo tehty.")
	else:
		aika = aika.split('-')
		for i in files:
			if i.rstrip('.csv') == aika[0]:
				yn = "y"
		if yn == "y": 
			filename = arch+aika[0]+".csv"
			try:
				file1 = open(filename, "a", encoding='utf-8')
				file2 = open(tempfile, "r", encoding='utf-8')
			except Exception:
				logging.error("Arkistotiedostoja ei pystytty avaamaan.")
				return
			
			rivi = file2.readline()
			file1.write(aika2)
			while len(rivi) > 0:
				file1.write(rivi[:-1]+";")
				rivi = file2.readline()
			file1.write("\n")
			file1.close()
			file2.close()
			os.remove(tempfile)
			archiveDate = aika3
			logging.info("Arkistointi olemassaolevaan tiedostoon onnistui.")
			
		else: #jos tiedostoa ei löydy
			logging.info("Arkistoa ei löytynyt. Luodaan uusi.")
			filename = arch+aika[0]+".csv"
			try:
				file1 = open(filename, "w", encoding='utf-8')
				file2 = open(tempfile, "r", encoding='utf-8')
			except Exception:
				logging.error("Arkistotiedostoja ei pystytty avaamaan.")
				return
			
			rivi = file2.readline()
			file1.write(aika2)
			while len(rivi) > 0:
				file1.write(rivi[-1]+";")
				rivi = file2.readline()
			file1.write("\n")
			file1.close()
			file2.close()
			os.remove(tempfile)
			archiveDate = aika3
			logging.info("Tallennus uuteen tiedostoon onnistui.")
			

def utflen(s): #str pituus bitteinä
    return len(s.encode('utf-8'))
				
def defineScreen(): #muuttujien määritys, KÄYTÄ VAIN KERRAN KÄYNNISTYKSEN YHTEYDESSÄ
	logging.info("Alustetaan näyttöön liittyvät muuttujat.")
	epd = epd2in7b.EPD()
	epd.init()
	
	screenState = 1
	epd.Clear(0xFF)
	epd.sleep()
	screenState = 0
	
	return epd

def clear(epd): #tyhjennä näyttö
	logging.info("Clearing screen...")
	epd.Clear(0xFF)
	
def Buttons(epd, info):
	key1 = Button(5)
	key2 = Button(6)
	key3 = Button(13)
	key4 = Button(19)
	while True:
		if key1.is_pressed: # Nykyinen PAC
			logging.info("Key 1 pressed! PAC")
			solarData = GetInverterData(info)
			if screenState == 1:
				time.sleep(25)
			if solarData == -1:
				screenState = 1
				draw(solarData, epd, DrawType=0)
				screenState = 0
			else:
				screenState = 1
				draw(solarData.PAC, epd, DrawType=1)
				screenState = 0
			time.sleep(1)
			
		if key2.is_pressed: # Päivän tuotto
			logging.info("Key 2 pressed! DAY_ENERGY")
			solarData = GetInverterData(info)
			if screenState == 1:
				time.sleep(25)
			if solarData == -1:
				screenState = 1
				draw(solarData, epd, DrawType=0)
				screenState = 0
			else:
				screenState = 1
				draw(solarData.day_energy, epd, DrawType=2)
				screenState = 0
			time.sleep(1)
			
		if key3.is_pressed: # Vuoden tuotto
			logging.info("Key 3 pressed! YEAR_ENERGY")
			solarData = GetInverterData(info)
			if screenState == 1:
				time.sleep(25)
			if solarData == -1:
				screenState = 1
				draw(solarData, epd, DrawType=0)
				screenState = 0
			else:
				screenState = 1
				draw(solarData.year_energy, epd, DrawType=3)
				screenState = 0
			time.sleep(1)
		
		if key4.is_pressed: #SHUTDOWN (Päivän suurin tuotto ?)
			logging.info("Key 4 pressed! SHUTDOWN")
			solarData = 0
			if screenState == 1:
				time.sleep(25)
			screenState = 1
			draw(solarData, epd, DrawType=4)
			time.sleep(1)
			os.system("shutdown")
			logging.info("Shutdown schduled.")

def draw(DataToDraw, epd, DrawType): #Piirrä näytölle
	
	HBlackimage = Image.new('1', (epd2in7b.EPD_HEIGHT, epd2in7b.EPD_WIDTH), 255)  # 298*126
	HRedimage = Image.new('1', (epd2in7b.EPD_HEIGHT, epd2in7b.EPD_WIDTH), 255)  # 298*126
	drawblack = ImageDraw.Draw(HBlackimage)
	drawred = ImageDraw.Draw(HRedimage)
	font25 = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSerif.ttf', 25)
	font30 = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSerif.ttf', 30)
	font40 = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSerif.ttf', 40)
	drawblack.rectangle((5, 5, 258, 170), outline = 0)
	drawblack.rectangle((6, 6, 257, 169), outline = 0)
	drawblack.rectangle((7, 7, 256, 168), outline = 0)
	
	DataToDraw = int(DataToDraw)
	
	if DataToDraw == -1: # Ei dataa
		drawred.text((30, 105), 'YHTEYSVIRHE', font = font30, fill = 0)
		drawred.text((150, 25), '---', font = font40, fill = 0)
		
	elif DrawType==4:
		drawred.text((30, 105), 'POWER OFF', font = font30, fill = 0)
		drawred.text((150, 25), '---', font = font40, fill = 0)
		
	else:
		if len(str(DataToDraw)) >=4: # Jos on kilowatteja
			DataToDraw = DataToDraw / 1000
			if len(str(DataToDraw)) <= 8:
				DataToDraw = round(DataToDraw, 3)
			elif len(str(DataToDraw)) > 8:
				DataToDraw = round(DataToDraw)
			drawred.text((195, 120), 'kW', font = font25, fill = 0)
				
		else:
			drawred.text((195, 120), 'W', font = font25, fill = 0)
		
		if DrawType == 1:
			if DataToDraw < 500:
				weather = Image.open(polku+'pilvi.bmp')
			elif DataToDraw > 500 and DataToDraw < 1500:
				weather = Image.open(polku+'aurinko2.bmp')
			elif DataToDraw > 1500:
				weather = Image.open(polku+'aurinko1.bmp')
			HBlackimage.paste(weather, (30,25)) 
			
		if DrawType==1:
			drawred.text((150, 25), 'PAC', font = font40, fill = 0)
		elif DrawType==2:
			drawred.text((150, 25), 'DAY', font = font40, fill = 0)
		elif DrawType==3:
			drawred.text((135, 25), 'YEAR', font = font40, fill = 0)
		elif DrawType==4:
			drawred.text((30, 105), 'POWER OFF', font = font30, fill = 0)
			drawred.text((150, 25), '---', font = font40, fill = 0)
		
		
		drawred.text((30, 105), str(DataToDraw), font = font40, fill = 0)
	
	logging.info("Screen set")
	epd.init()

	clear(epd)
	logging.info("Drawing to screen...")
	epd.display(epd.getbuffer(HBlackimage), epd.getbuffer(HRedimage))
	logging.info("Setting screen to sleep...")
	epd.sleep()
	
def paaohjelma(info, epd):
	kello = time.strftime("%H-%M-%S")
		
	if int(kello.split('-')[0]) >= 23 and int(kello.split('-')[1]) >= 54:
		archive()
		
	else:
		solarData = GetInverterData(info)
		if solarData == -1:
			if screenState == 1:
				time.sleep(25)
			screenState = 1
			draw(solarData, epd, DrawType=0)
			screenState = 0
			
		else:
			if screenState == 1:
				time.sleep(25)
			tempSaveData(solarData)
			screenState = 1
			draw(solarData.PAC, epd, DrawType=1)
			screenState = 0
		
def aikataulu(info, epd):
	time.sleep(16)
	solarData = GetInverterData(info)
	if solarData == -1:
		if screenState == 1:
			time.sleep(25)
		screenState = 1
		draw(solarData, epd, DrawType=0)
		screenState = 0
		
	else:
		if screenState == 1:
			time.sleep(25)
		screenState = 1
		draw(solarData.PAC, epd, DrawType=1)
		screenState = 0

	schedule.every(5).minutes.do(paaohjelma, info, epd)
	while True:
		schedule.run_pending()
		time.sleep(1)

def main():
	time.sleep(30)
	logname = arch+'SolarVIZ_log.log'
	logging.basicConfig(filename=logname, level=logging.DEBUG, format='%(asctime)s %(levelname)s - %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
	startInfo = StartUp()
	epd = defineScreen()
	p1 = multiprocessing.Process(name='paaohjelma', target=aikataulu, args=(startInfo, epd))
	p2 = multiprocessing.Process(name='Buttons', target=Buttons, args=(epd, startInfo))
	#p3 = multiprocessing.Process(name='server', target=mainServer)

	logging.debug("Main_START")
	p1.start()
	time.sleep(40)
	logging.debug("BUTTONS_START")
	p2.start()
	#p3.start()

if __name__ == '__main__':
    main()
