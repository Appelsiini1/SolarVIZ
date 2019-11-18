# SolarVIZ Server 
# v0.0 (19.07.2019)
# v0.1 (23.07.2019)
# v0.2 (01.08.2019)
# v0.3 (06.08.2019)
# v0.4 (08.08.2019)
# v0.5 (11.08.2019)
# v0.9 (29.08.2019)
# (c) Rami Saarivuori 2019
# All rights reserved

VIZversion = "0.9"
polku = '//home//pi//SolarVIZ//' # absoluuttinen polku tarvitaan, jotta ohjelma toimii crontabin kanssa oikein

try:
	from urllib import request as rq
	import schedule, multiprocessing, time, socket, os, epd2in7b
	from datetime import date
	from PIL import Image,ImageDraw,ImageFont
	from gpiozero import Button
except Exception:
	print("Kirjastojen tuonti epäonnistui, lopetetaan.")
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
	print("Initializing...")
	try:
		name = polku + "config.txt"
		tdsto = open(name, "r", encoding="utf-8")
		startState = 0 # tiedosto löytyi, eli ei ensimmäinen kerta
	except FileNotFoundError: #tiedostoa ei löydetty
		startState = 1
		pass
		
	if startState == 1: #koska tiedostoa ei löydetty, kysytään ohjelman toiminnan kannalta oleelliset tiedot "config" tiedostoon
		info = []
		print("Tervetuloa käyttämään SolarVIZ -ohjelmistoa, jonka tarkoituksena on kerätä, arkistoida ja visualisoida aurinkosähköjärjestelmien tuottamaa dataa. Ohjelma on tällä hetkellä yhteensopiva FRONIUS invertterien kanssa, jotka tukevat FRONIUS Solar API:n versiota 1.")
		time.sleep(1)
		print("Aloitetaan käyttöönotto.")
		time.sleep(1)
		nimi = input("Anna järjestelmällesi nimi: ") #ihan vaan visuaalisuuden vuoksi
		time.sleep(1)
		MAX_P = input("Anna järjestelmän maksimituotto (W): ") #kuvaajia varten
		time.sleep(1)
		InverterIP = input("Anna invertterin IP-osoite (muodossa 123.456.789.012): ")#tärkein asia toiminnan kannalta, ilman tätä ohjelma ei pysty toimimaan
		InverterIP.strip("\n")
		
		#Tähän vielä jotain IP-osoitteen muodollisuuden tarkistusta?
		#Ja että MAX_P on luku?
		
		info.append(nimi)
		info.append(MAX_P)
		info.append(InverterIP)
		
		file = open(name, "w", encoding="utf-8")
		file.write("SolarVIZ, V"+VIZversion+" configuration for '"+nimi+"'\n") #kirjoitetaan asetustiedosto
		for i in info:
			file.write(i+"\n")
			
		file.close()
		return info
		
	elif startState == 0:
		info = []
		rivi = tdsto.readline()
		while True:
			rivi = tdsto.readline()
			if len(rivi) == 0:
				break
			
			print(rivi[:-1])
			info.append(rivi[:-1])
		tdsto.close()
		print("Initialization successfull.")
		return info

#def catch_exceptions(cancel_on_failure=False): # virheestä toipuminen (schedule-kirjaston vuoksi)
    #def catch_exceptions_decorator(job_func):
        #@functools.wraps(job_func)
        #def wrapper(*args, **kwargs):
            #try:
                #return job_func(*args, **kwargs)
            #except:
                #import traceback
                #print(traceback.format_exc())
                #if cancel_on_failure:
                    #return schedule.CancelJob
        #return wrapper
    #return catch_exceptions_decorator
	
#@catch_exceptions(cancel_on_failure=False)

def GetInverterData(info): # haetaan data rajapinnan kautta invertteriltä
	print("Muodostetaan yhteys invertteriin...")
	try:
		solarData = rq.urlopen("http://"+info[2]+"/solar_api/v1/GetInverterRealtimeData.cgi?Scope=System")
	except: #invertteriin ei saatu yhteyttä
		print("Virhe muodostettaessa yhteyttä invertteriin.")
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
	print("Data järjestelty.")
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
	
	if int(kello.split('-')[0]) == 7 and int(kello.split('-')[1]) <= 4:
		file = open(name, "w", encoding='utf-8')
		tallennus = kello+":"+solarData.PAC+":"+solarData.day_energy+"\n"
		file.write(tallennus)
		file.close()
		print("Tallennus onnistui. (Klo 7)")
		
	elif int(kello.split('-')[0]) >= 23 and int(kello.split('-')[1]) >= 0:
		file = open(name, "a", encoding='utf-8')
		tallennus = kello+":"+solarData.PAC+":"+solarData.day_energy+":"+solarData.year_energy+":"+solarData.total_energy+"\n"
		file.write(tallennus)
		file.close()
		print("Tallennus onnistui. Klo 23")
		
	elif yn == "y":
		file = open(name, "a", encoding='utf-8')
		tallennus = kello+":"+solarData.PAC+":"+solarData.day_energy+"\n"
		file.write(tallennus)
		file.close()
		print("Tallennus onnistui. (A)")
		
	else:
		file = open(name, "w", encoding='utf-8')
		tallennus = kello+":"+solarData.PAC+":"+solarData.day_energy+"\n"
		file.write(tallennus)
		file.close()
		print("Tallennus onnistui. (B)")

def archive(): #pitempi aikainen tallennus taulukkoon (päivän lopuksi)
	print("Aloitetaan arkistointi.")
	aika = date.today().strftime("%Y-%m-%d")
	aika2 = aika+"\n"
	tempfile = polku+aika+".txt"
	files = os.listdir(polku)
	yn = "n"
	aika = aika.split('-')
	for i in files:
		if i.rstrip('.csv') == aika[0]:
			yn = "y"
	if yn == "y": 
		filename = polku+aika[0]+".csv"
		file1 = open(filename, "a", encoding='utf-8')
		file2 = open(tempfile, "r", encoding='utf-8')
		
		rivi = file2.readline()
		file1.write(aika2)
		while len(rivi) > 0:
			file1.write(rivi[:-1]+";")
			rivi = file2.readline()
		file1.write("\n")
		file1.close()
		file2.close()
		os.remove(tempfile)
		print("Arkistointi olemassaolevaan tiedostoon onnistui.")
		
	else: #jos tiedostoa ei löydy
		print("Arkistoa ei löytynyt. Luodaan uusi.")
		filename = polku+aika[0]+".csv"
		file1 = open(filename, "w", encoding='utf-8')
		file2 = open(tempfile, "r", encoding='utf-8')
		
		rivi = file2.readline()
		file1.write(aika2)
		while len(rivi) > 0:
			file1.write(rivi[-1]+";")
			rivi = file2.readline()
		file1.write("\n")
		file1.close()
		file2.close()
		os.remove(tempfile)
		print("Tallennus uuteen tiedostoon onnistui.")

def utflen(s): #str pituus bitteinä
    return len(s.encode('utf-8'))

def mainServer(): #server loop
	print("Palvelin käynnistyy...")
	while True:
		aika = date.today().strftime("%Y-%m-%d")
	
		host = socket.gethostname()
		port = 5000  # initiate port (no below 1024)

		server_socket = socket.socket()  # get instance
		
		# look closely. The bind() function takes tuple as argument
		server_socket.bind((host, port))  # bind host address and port together

		# configure how many client the server can listen simultaneously
		server_socket.listen(5)
		conn, address = server_socket.accept()  # accept new connection
		print("Connection from: " + str(address))
		data = "OK"
		conn.send(data.encode())
				
		config = open(polku+"config.txt", "r", encoding="utf-8")
		info = []
		config.readline()
		info.append(config.readline())
		info.append(config.readline())
		info.append(config.readline())
		config.close()
		
		while True:
			# receive data stream. it won't accept data packet greater than 4096 bytes # data = conn.recv(4096).decode() # if not data: # # if data is not received break # break # print("from connected user: " + str(data))
			RecData = conn.recv(4096).decode()
			
			# 1 = Today's energy, 2 = Month energy, 3 = Year energy, 4 = Total energy, 5 = Current energy, 6 = Send archive, 9 = Close connection ;; 01-12 = Month (00 = N/A) ;; Year (esim. 2019) (0 = N/A)
			
			if RecData[0] == "1":
				print("Pyydetty päivän energia.")
				name = polku+aika + ".txt"
				file = open(name, "r", encoding='utf-8')
				
				rivi = file.readline()
				DayEnergy = []
				DayEnergyTotal = 0
				while len(rivi) > 1:
					rivi.split(":")
					pituus = len(rivi) - 1
					DayEnergy.append(rivi[pituus][1])
					DayEnergyTotal = MonthEnergyTotal + rivi[pituus][2]
					rivi = file.readline()
				
				DataToSend = str(DayEnergy).lstrip("[").rstrip("]") + ", " + str(DayEnergyTotal)
				if utflen(DataToSend) > 4096:
					pituus = len(DataToSend)
					pituus4 = round(pituus/4)
					osa1 = DataToSend[:pituus4]
					conn.send(osa1.encode())
					time.sleep(0.2)
					osa2 = DataToSend[pituus4:pituus4*2]
					conn.send(osa2.encode())
					time.sleep(0.2)
					osa3 = DataToSend[pituus4*2:pituus*3]
					conn.send(osa3.encode())
					time.sleep(0.2)
					osa4 = DataToSend[pituus4*3:]
					conn.send(osa4.encode())
					DataToSend = "eot"
					conn.send(DataToSend.encode())
					print("Datan lähetys onnistui.")
				else:
					conn.send(DataToSend.encode())
					DataToSend = "eot"
					conn.send(DataToSend.encode())
					print("Datan lähetys onnistui.")					
				
			elif RecData[0] == "2":
				print("Pyydetty kuukauden energiaa.")
				fname = polku+RecData[7:]+".csv"
				file = open(fname, "r", encoding=('utf-8'))
				kuukausi = RecData[3:5]
				while True:
					rivi.readline()
					if rivi[5:7] == kuukausi:
						break
						
				rivi = file.readline()
				MonthEnergy = []
				MonthEnergyTotal = 0
				while len(rivi) > 1:
					if len(rivi) < 12 and rivi[5:7] != kuukausi:
						break
					rivi.split(";")
					pituus = len(rivi) - 1
					MonthEnergy.append(rivi[pituus][2])
					MonthEnergyTotal = MonthEnergyTotal + rivi[pituus][2]
					rivi = file.readline()
						
				file.close()
				DataToSend = str(MonthEnergy).lstrip("[").rstrip("]") + ", " + str(MonthEnergyTotal)
				if utflen(DataToSend) > 4096:
					pituus = len(DataToSend)
					pituus4 = round(pituus/4)
					osa1 = DataToSend[:pituus4]
					conn.send(osa1.encode())
					time.sleep(0.5)
					osa2 = DataToSend[pituus4:pituus4*2]
					conn.send(osa2.encode())
					time.sleep(0.5)
					osa3 = DataToSend[pituus4*2:pituus*3]
					conn.send(osa3.encode())
					time.sleep(0.5)
					osa4 = DataToSend[pituus4*3:]
					conn.send(osa4.encode())
					DataToSend = "eot"
					conn.send(DataToSend.encode())
					print("Datan lähetys onnistui.")
				else:
					conn.send(DataToSend.encode())
					DataToSend = "eot"
					conn.send(DataToSend.encode())
					print("Datan lähetys onnistui.")
			
			elif RecData[0] == "3":
				print("Pyydetty tämän vuoden energiaa.")
			
				#tämä jos vuosi on kuluva vuosi
				ReturnedData = GetInverterData(info)
				if ReturnedData == -1:
					DataToSend = "Exception: 01"
					conn.send(DataToSend.encode())
					print("Datan lähetys onnistui. (Virhe: yhteyden muodostus invertteriin epäonnistui.)")
				else:
					solarData = cleanData(ReturnedData)
					DataToSend = solarData.year_energy
					conn.send(DataToSend.encode())
					print("Datan lähetys onnistui.")
					
			elif RecData[0] == "4":
				
				ReturnedData = GetInverterData(info)
				if ReturnedData == -1:
					DataToSend = "Exception: 01"
					conn.send(DataToSend.encode())
					print("Datan lähetys onnistui. (Virhe: yhteyden muodostus invertteriin epäonnistui.)")
				else:
					solarData = cleanData(ReturnedData)
					DataToSend = solarData.total_energy
					conn.send(DataToSend.encode())
					print("Datan lähetys onnistui.")
			
			elif RecData[0] == "5":
				
				ReturnedData = GetInverterData(info)
				if ReturnedData == -1:
					DataToSend = "Exception: 01"
					conn.send(DataToSend.encode())
					print("Datan lähetys onnistui. (Virhe: yhteyden muodostus invertteriin epäonnistui.)")
				else:
					solarData = cleanData(ReturnedData)
					DataToSend = solarData.PAC
					conn.send(DataToSend.encode())
					print("Datan lähetys onnistui.")
					
			elif RecData[0] == "6":
				fname = polku+RecData[7:]+".csv"
				file = open(fname, "r", encoding=('utf-8'))
				
				DataToSend = file.read(4096)
				
				while DataToSend > 1:
					conn.send(DataToSend.encode())
					DataToSend = file.read(4096)
					time.sleep(0.5)
					
				
				DataToSend = "eot"
				conn.send(DataToSend.encode())
				print("Datan lähetys onnistui.")
							
			elif RecData[0] == "9":
				conn.close()  # close the connection
				print("Yhteys suljettu.")
				break
				
class screen: #screen functions
	def defineStart(): #muuttujien määritys, KÄYTÄ VAIN KERRAN KÄYNNISTYKSEN YHTEYDESSÄ
		print("Alustetaan näyttöön liittyvät muuttujat.")
		epd = epd2in7b.EPD()
		epd.init()

		key1 = Button(5)
		key2 = Button(6)
		key3 = Button(13)
		key4 = Button(19)
		
		epd.Clear(0xFF)
		epd.sleep()
		
		return epd, key1, key2, key3, key4
	
	def clear(epd): #tyhjennä näyttö
		print("Clearing screen...")
		epd.Clear(0xFF)
		
	def Buttons(epd, key1, key2, key3, key4, info):
		while True:
			if key1.is_pressed: # Nykyinen PAC
				print("Key 1 pressed!")
				solarData = GetInverterData(info)
				if solarData == 0:
					screen.draw(solarData, epd, DrawType=0)
				else:
					screen.draw(solarData.PAC, epd, DrawType=1)
				
			if key2.is_pressed: # Päivän tuotto
				print("Key 2 pressed!")
				solarData = GetInverterData(info)
				if solarData == 0:
					screen.draw(solarData, epd, DrawType=0)
				else:
					screen.draw(solarData.day_energy, epd, DrawType=2)
				
			if key3.is_pressed: # Vuoden tuotto
				print("Key 3 pressed!")
				solarData = GetInverterData(info)
				if solarData == 0:
					screen.draw(solarData, epd, DrawType=0)
				else:
					screen.draw(solarData.year_energy, epd, DrawType=3)
			
			if key4.is_pressed: #SHUTDOWN (Päivän suurin tuotto ?)
				print("Key 4 pressed!")
				solarData = 0
				screen.draw(solarData, epd, DrawType=4)
				time.sleep(1)
				os.system("shutdown now -h")

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
		
		print("Screen set")
		epd.init()

		screen.clear(epd)
		print("Drawing to screen...")
		epd.display(epd.getbuffer(HBlackimage), epd.getbuffer(HRedimage))
		print("Setting screen to sleep...")
		epd.sleep()
	
def paaohjelma(info, epd):
	kello = time.strftime("%H-%M-%S")
		
	if int(kello.split('-')[0]) >= 23 and int(kello.split('-')[1]) >= 4:
		archive()
		
	elif int(kello.split('-')[0]) >= 23 and int(kello.split('-')[1]) > 5:
		pass
	elif int(kello.split('-')[0]) >= 0 and int(kello.split('-')[1]) >= 0 and int(kello.split('-')[0]) <= 6:
		pass

		
	else:
		solarData = GetInverterData(info)
		if solarData == -1:
			screen.draw(solarData, epd, DrawType=0)
			
		else:
			tempSaveData(solarData)
			screen.draw(solarData.PAC, epd, DrawType=1)
		
def aikataulu(info, epd):
	time.sleep(16)
	solarData = GetInverterData(info)
	if solarData == -1:
		screen.draw(solarData, epd, DrawType=0)
		
	else:
		screen.draw(solarData.PAC, epd, DrawType=1)
	schedule.every(5).minutes.do(paaohjelma, info, epd)
	while True:
		schedule.run_pending()
		time.sleep(1)


startInfo = StartUp()
epd, key1, key2, key3, key4 = screen.defineStart()
p1 = multiprocessing.Process(name='paaohjelma', target=aikataulu, args=(startInfo, epd))
p2 = multiprocessing.Process(name='Buttons', target=screen.Buttons, args=(epd, key1, key2, key3, key4, startInfo))
p3 = multiprocessing.Process(name='server', target=mainServer)

p1.start()
p2.start()
#p3.start()
