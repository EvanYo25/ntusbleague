# -*- coding: utf-8 -*-

from django.shortcuts import render, redirect
from models import Team,Member,Game,Pitching,Batting,Schedule
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from data import Hitter, Pitcher, TeamStat, GameStat, League
from operator import attrgetter
from django.contrib.auth import authenticate, login as log_account , logout as out_account
from django.contrib.auth.models import User
from parse_record import parse_game_record, text_to_table
from player import rdBatter, rdPitcher
from django.http import HttpResponse
import mimetypes, os
from wsgiref.util import FileWrapper
from django.core.exceptions import ObjectDoesNotExist


# Create your views here.
def index(request) : 

	team_list={}
	
	games = Game.objects.filter(gameID__gte = 4000)
	
	# --- team ranking
	teams = Team.objects.filter(current__gte = 1)

	team_list=[]
	team_map = {}
	for team in teams:
		t = TeamStat()
		t.name 		= team.name
		t.teamID 	= team.teamID
		t.current 	= team.current
		team_map[team.teamID] = t

	for game in games:
		awayID = game.away.teamID
		homeID = game.home.teamID
		
		team_map[awayID].game_played += 1
		team_map[homeID].game_played += 1

		result = game.get_result()
		if( not result ): # tie
			team_map[awayID].tie += 1
			team_map[homeID].tie += 1
		else:
			team_map[result[0].teamID].win  += 1
			team_map[result[1].teamID].lose += 1

	for team in team_map.values():
		team.stat()
		team_list.append(team)
		# if(team.current == 1):
		# 	league_list[0].team_list.append(team)
		# else: # current == 2
		# 	league_list[1].team_list.append(team)

	
	team_list = sorted(team_list, key=attrgetter('percent'), reverse=True)

	top = team_list[0]
	for team in team_list:
		team.GB = ( (top.win - team.win) + (team.lose -  top.lose) ) / 2.0

	team_list = sorted(team_list , key=attrgetter('percent'), reverse=True)
	team_list = sorted(team_list , key=attrgetter('GB'))
	team_list[0].GB = '-'
	


	players = Member.objects.all()
	# --- batting ranking
	thr = 1
	batting_list = calculate_batting_rank(players)
	batting_list = filter(lambda list : not list.name.startswith("OB"),batting_list)

	batting_list = sorted(batting_list, cmp=lambda x,y:cmp(int(y.pa),int(x.pa)))
	batting_list = sorted(batting_list, cmp=lambda x,y:cmp(float(y.avg),float(x.avg)))
	avg_list = batting_list[0:5]

	batting_list = sorted(batting_list, cmp=lambda x,y:cmp(float(y.avg),float(x.avg)))
	batting_list = sorted(batting_list, cmp=lambda x,y:cmp(int(y.hit),int(x.hit)))
	hit_list = batting_list[0:5]

	batting_list = sorted(batting_list, cmp=lambda x,y:cmp(int(x.pa),int(y.pa)))
	batting_list = sorted(batting_list, cmp=lambda x,y:cmp(int(y.hr),int(x.hr)))
	hr_list = batting_list[0:5]

	batting_list = sorted(batting_list, cmp=lambda x,y:cmp(int(y.rbi),int(x.rbi)))
	rbi_list = batting_list[0:5]

	# --- pitching ranking
	thr = 1
	pitching_list = calculate_pitching_rank(players,thr)
	pitching_list = filter(lambda list : not list.name.startswith("OB"),pitching_list)

	pitching_list = sorted(pitching_list, cmp=lambda x,y : cmp(int(y.outs),float(x.outs)))
	pitching_list = sorted(pitching_list, cmp=lambda x,y : cmp(float(x.era),float(y.era)))
	era_list = pitching_list[0:5]

	pitching_list = sorted(pitching_list, cmp=lambda x,y : cmp(float(x.era),float(y.era)))
	pitching_list = sorted(pitching_list, cmp=lambda x,y : cmp(int(y.win),float(x.win)))
	win_list = pitching_list[0:5]

	pitching_list = sorted(pitching_list, cmp=lambda x,y : cmp(int(x.outs),float(y.outs)))
	pitching_list = sorted(pitching_list, cmp=lambda x,y : cmp(int(y.so),float(x.so)))
	so_list = pitching_list[0:5]

	pitching_list = sorted(pitching_list, cmp=lambda x,y : cmp(float(x.era),float(y.era)))
	pitching_list = sorted(pitching_list, cmp=lambda x,y : cmp(float(x.whip),float(y.whip)))
	whip_list = pitching_list[0:5]
	

	context = {'team_list' : team_list, 'avg_list': avg_list, 'hit_list': hit_list, 'hr_list': hr_list, 'rbi_list': rbi_list, 'era_list': era_list, 'win_list': win_list, 'so_list': so_list, 'whip_list': whip_list}
	
	return render (request, 'sbleague/index.html', context)

def calculate_batting_rank(players,year=4):
	
	player_map = {}
	batting_all = Batting.objects.filter(game__gameID__gte=year*1000)

	teams=Team.objects.all()
	team_gamecount=[]
	for team in teams:
		home=Game.objects.filter(home=team,gameID__gte=year*1000).count()
		away=Game.objects.filter(away=team,gameID__gte=year*1000).count()
		count=home+away
		team_gamecount.append([team,count])

	for batting in batting_all:
		id = batting.member.memberID
		if( not player_map.has_key(id) ):
			h 			= Hitter()
			h.name 		= batting.member.name
			h.memberID 	= batting.member.memberID
			h.team 		= batting.team
			h.teamID	= batting.team.teamID
			player_map[id] = h
			player_map[id].id = id

		player_map[id].pa 			+= batting.pa
		player_map[id].single 		+= batting.single
		player_map[id].double 		+= batting.double
		player_map[id].triple 		+= batting.triple
		player_map[id].hr 			+= batting.hr
		player_map[id].rbi 			+= batting.rbi
		player_map[id].r 			+= batting.run
		player_map[id].bb			+= batting.bb
		player_map[id].so 			+= batting.so
		player_map[id].sf 			+= batting.sf
		player_map[id].games_played += 1


	for player in player_map.values():
		if len(team_gamecount)!=0 :
			for team in team_gamecount:
				if team[0] == player.team:
					if team[1]*2 <= player.pa:
						player.stat()
					else:
						del player_map[player.id]
		else :
			player.stat()

	batting_list = player_map.values()

	return batting_list

def calculate_pitching_rank(players,thr=0,year=4):
	
	player_map = {}
	pitching_all = Pitching.objects.filter(pa__gte=thr,game__gameID__gte=year*1000)
	
	teams=Team.objects.all()
	team_gamecount=[]
	for team in teams:
		home=Game.objects.filter(home=team).count()
		away=Game.objects.filter(away=team).count()
		count=home+away
		team_gamecount.append([team,count])

	for pitching in pitching_all:
		id = pitching.member.memberID
		if( not player_map.has_key(id) ):
			h 			= Pitcher()
			h.name 		= pitching.member.name
			h.memberID 	= pitching.member.memberID
			h.team 		= pitching.team
			h.teamID	= pitching.team.teamID
			player_map[id] = h
			player_map[id].id = id

		player_map[id].pa 			+= pitching.pa
		player_map[id].win 			+= pitching.win
		player_map[id].lose 		+= pitching.lose
		player_map[id].bb			+= pitching.bb
		player_map[id].so 			+= pitching.so
		player_map[id].h 			+= pitching.h
		player_map[id].hr 			+= pitching.hr
		player_map[id].r 			+= pitching.r
		player_map[id].outs			+= pitching.outs
		player_map[id].er			+= pitching.er
		player_map[id].go			+= pitching.go
		player_map[id].fo			+= pitching.fo
		player_map[id].games_played += 1

	for player in player_map.values():
		if len(team_gamecount)!=0 :
			for team in team_gamecount:
				if team[0] == player.team:
					if team[1]*2 <= player.outs:
						print"-", player.name , team[1]*9 , player.outs
						player.stat()
					else:
						del player_map[player.id]

		else:
			player.stat()

	pitching_list = player_map.values()
	return pitching_list

def allbatting(request, order="avg"):
	
	players = Member.objects.all() 
	batting_list = calculate_batting_rank(players)
	batting_list = sorted(batting_list, key=attrgetter(order), reverse=True)

	context = {'batting_list': batting_list}
	return render(request , 'sbleague/allbatting.html',context)


def allpitching(request, order="win"):
    
	increase_order = ["era", "whip", "bb_inning", "er", "r", "hr", "h", "bb"]
	if( order in increase_order ):
		rev = False
	else:
		rev = True
	
	players = Member.objects.all()
	pitching_list = calculate_pitching_rank(players)
	pitching_list = sorted(pitching_list, key=attrgetter(order), reverse=rev)

	context = {'pitching_list': pitching_list}
	return render(request , 'sbleague/allpitching.html',context)

def team(request , team_id , order="hit",y=4) :
	thisteam = Team.objects.get(teamID = team_id)
	team_info = TeamStat()	#init
	team_info.name 	 = thisteam.name
	team_info.teamID = thisteam.teamID
	team_overall={}  #勝敗和那邊

	game_all = Game.objects.filter(Q(away = team_id) | Q(home = team_id)).order_by('gameID')
	game_list = []
	for game in game_all:
		year = game.gameID/1000 + 2011

		if not team_overall.has_key(year) :
			team_overall[year]=TeamStat()
			team_overall[year].year=year;
			team_overall[year].win=0;
			team_overall[year].lose=0;
			team_overall[year].tie=0;
			team_overall[year].game_played=0;
			

		g = GameStat()

		if( game.away.teamID != int(team_id) ):
			opp = game.away
		else:
			opp = game.home

		game_result = game.get_result()
		if( len(game_result) == 0 ):
			result = '和'
			team_overall[year].tie += 1
		elif( game_result[0].teamID == int(team_id) ):
			result = '勝'
			team_overall[year].win += 1
		else:
			result = '敗'
			team_overall[year].lose += 1

		team_overall[year].game_played += 1

		scores = game.get_scores()

		if game.gameID >= y*1000 and game.gameID <= (y+1)*1000: 
			
			g.gameID 	= game.gameID
			g.date 		= game.date
			g.location 	= game.location
			g.opp 		= opp
			g.scores 	= str(sum(scores[0])) + ' : ' + str(sum(scores[1]))
			g.result 	= result
			game_list.append(g)
	
	# sort by date


	game_list = sorted(game_list , key=attrgetter('date'))

	members = Member.objects.filter(team__teamID = team_id)

	members_bat= []
	members_pit= []
	team_bat = Hitter()
	team_pit = Pitcher()

	for player in members:
		#batting data
		bat = Batting.objects.filter(member__memberID = player.memberID , team = thisteam.teamID,game__gameID__gte=y*1000)
		
		if bat.exists() :
			hitter = Hitter()
			for bat_detail in bat:
				hitter.name = player.name
				hitter.id = player.memberID
				hitter.games_played += 1
				hitter.pa += bat_detail.pa
				hitter.single +=bat_detail.single
				hitter.double +=bat_detail.double
				hitter.triple +=bat_detail.triple
				hitter.hr += bat_detail.hr
				hitter.rbi += bat_detail.rbi
				hitter.r += bat_detail.run
				hitter.bb+= bat_detail.bb
				hitter.so +=bat_detail.so
				hitter.sf +=bat_detail.sf
			hitter.stat()
			members_bat.append(hitter)
			team_bat.add(hitter)
			team_bat.stat()
		# evan code
		else:
			hitter = Hitter()
			hitter.name = player.name
			hitter.id = player.memberID
			hitter.games_played = 0
			hitter.pa = 0
			hitter.single = 0
			hitter.double = 0
			hitter.triple = 0
			hitter.hr = 0
			hitter.rbi = 0
			hitter.r = 0
			hitter.bb = 0
			hitter.so = 0
			hitter.sf = 0
			hitter.stat()
			members_bat.append(hitter)
			team_bat.add(hitter)
			team_bat.stat()
		# end evan code
		members_bat=sorted(members_bat,key=attrgetter(order),reverse=True)

		#pitching data
		pit = Pitching.objects.filter(member__memberID = player.memberID , team = thisteam.teamID,game__gameID__gte=y*1000)
		if pit.exists() :
			pitcher = Pitcher()

			for pit_detail in pit:
				pitcher.name = player.name
				pitcher.games_played +=1
				pitcher.id = player.memberID
				pitcher.win+=pit_detail.win
				pitcher.lose+=pit_detail.lose
				pitcher.outs+=pit_detail.outs
				pitcher.pa+=pit_detail.pa
				pitcher.so+=pit_detail.so
				pitcher.bb+=pit_detail.bb
				pitcher.h+=pit_detail.h
				pitcher.hr+=pit_detail.hr
				pitcher.r+=pit_detail.r
				pitcher.er+=pit_detail.er
				pitcher.go+=pit_detail.go
				pitcher.fo+=pit_detail.fo

			pitcher.stat()
			members_pit.append(pitcher)
			team_pit.add(pitcher)
			team_pit.stat()

	context = {'thisteam' : thisteam, 'team_info':team_info, 'game_list': game_list, 'members_bat': members_bat ,'members_pit':members_pit, 'team_bat' : team_bat, 'team_pit' : team_pit,'team_overall':team_overall}

	return render(request , 'sbleague/team.html',context)

def allteam(request,pos,order,year=4):
	teams = Team.objects.filter(current__gt=0)
	allteam_pit = []
	allteam_bat = []

	if pos == "bat" :
		league = Hitter()
		for t in teams :
			hitter=Hitter()
			bat_all = Batting.objects.filter(team=t.teamID,game__gameID__gte=year*1000)
			hitter.name = t.name
			hitter.id = t.teamID
			for bat_detail in bat_all :
				hitter.pa += bat_detail.pa
				hitter.single +=bat_detail.single
				hitter.double +=bat_detail.double
				hitter.triple +=bat_detail.triple
				hitter.hr += bat_detail.hr
				hitter.rbi += bat_detail.rbi
				hitter.r += bat_detail.run
				hitter.bb+= bat_detail.bb
				hitter.so +=bat_detail.so
				hitter.sf +=bat_detail.sf
			hitter.stat()
			allteam_bat.append(hitter)
			league.add(hitter)
		pos = "打擊"
		allteam_bat=sorted(allteam_bat,key=attrgetter(order),reverse=True)

	elif pos == "pit":
		league = Pitcher()
		for t in teams: 
			pitcher = Pitcher()
			pit_all = Pitching.objects.filter(team=t.teamID,game__gameID__gte=year*1000)
			pitcher.id = t.teamID
			pitcher.name=t.name
			for pit_detail in pit_all :
				pitcher.win+=pit_detail.win
				pitcher.lose+=pit_detail.lose
				pitcher.outs+=pit_detail.outs
				pitcher.pa+=pit_detail.pa
				pitcher.so+=pit_detail.so
				pitcher.bb+=pit_detail.bb
				pitcher.h+=pit_detail.h
				pitcher.hr+=pit_detail.hr
				pitcher.r+=pit_detail.r
				pitcher.er+=pit_detail.er
				pitcher.go+=pit_detail.go
				pitcher.fo+=pit_detail.fo

			pitcher.stat()
			allteam_pit.append(pitcher)
			league.add(pitcher)
		pos="投球"
		allteam_pit=sorted(allteam_pit,key=attrgetter(order),reverse=True)

	league.stat()
	context={'type':pos, 'teams_bat' : allteam_bat , 'teams_pit' : allteam_pit , 'league':league}
	return render(request , 'sbleague/allteam.html',context)


def people(request , member_id) :

	player = Member.objects.get(memberID = member_id)

	# --- batting
	game_all 	= Batting.objects.filter(member__memberID = member_id).order_by("game")
	hitting_list = []
	hitting_sum  = Hitter()
	
	if game_all.exists() :
		for game_detail in game_all:
			hitter 			= Hitter()
			hitter.pa 		= game_detail.pa
			hitter.single 	= game_detail.single
			hitter.double 	= game_detail.double
			hitter.triple 	= game_detail.triple
			hitter.hr 		= game_detail.hr
			hitter.rbi 		= game_detail.rbi
			hitter.r 		= game_detail.run
			hitter.bb		= game_detail.bb
			hitter.so 		= game_detail.so
			hitter.sf 		= game_detail.sf

			hitter.games_played = 1
			hitter.stat()
			hitting_sum.add(hitter)
			hitting_sum.stat()

			# accumulated statistic
			hitter.avg_s	= hitting_sum.avg_s
			hitter.slg_s	= hitting_sum.slg_s
			hitter.obp_s	= hitting_sum.obp_s
			hitter.ops_s	= hitting_sum.ops_s
			
			# game information
			game 			= game_detail.game
			hitter.date 	= str(game.date)
			hitter.gameID 	= str(game.gameID)

			# opponent team
			if( game_detail.team == game.home ):
				opp = game.away	
			else:
				opp = game.home

			hitter.opp 		= str(opp)
			hitter.oppID 	= str(opp.teamID)

			hitting_list.append(hitter)

	# --- pitching
	game_all  	  = Pitching.objects.filter(member__memberID = member_id).order_by("game")
	pitching_list = []
	pitching_sum  = Pitcher()
	
	if game_all.exists() :
		for game_detail in game_all:
			pitcher 		= Pitcher()
			pitcher.win 	= game_detail.win
			pitcher.lose 	= game_detail.lose
			pitcher.outs 	= game_detail.outs
			pitcher.pa 		= game_detail.pa
			pitcher.so 		= game_detail.so
			pitcher.bb 		= game_detail.bb
			pitcher.h		= game_detail.h
			pitcher.hr		= game_detail.hr
			pitcher.r 		= game_detail.r
			pitcher.er 		= game_detail.er
			pitcher.go 		= game_detail.go
			pitcher.fo 		= game_detail.fo

			pitcher.games_played = 1
			pitcher.stat()
			pitching_sum.add(pitcher)
			pitching_sum.stat()

			# accumulated statistic
			pitcher.bb_inning_s 	= pitching_sum.bb_inning_s
			pitcher.era_s 	= pitching_sum.era_s
			pitcher.whip_s 	= pitching_sum.whip_s
			
			# game information
			game 			= game_detail.game
			pitcher.date 	= str(game.date)
			pitcher.gameID 	= str(game.gameID)

			# opponent team
			if( game_detail.team == game.home ):
				opp = game.away	
			else:
				opp = game.home

			pitcher.opp 	= str(opp)
			pitcher.oppID 	= str(opp.teamID)

			pitching_list.append(pitcher)


	context = {'thispeople' : player, 'name': player.name, 'hitting_list': hitting_list, 'hitting_sum': hitting_sum, 'pitching_list': pitching_list, 'pitching_sum': pitching_sum, }

	return render(request, 'sbleague/people.html', context)

def allgame(request):

	schedule = Schedule.objects.all().order_by('-date')

	game_list = Game.objects.all().order_by('-date')

	for game in game_list:
		scores = game.get_scores()
		game.scores = str(sum(scores[0])) + ' : ' + str(sum(scores[1]))

	context = {'schedule': schedule, 'game_list': game_list}
	return render(request, 'sbleague/allgame.html', context)

def game(request , game_id) :

	g = Game.objects.get(gameID = game_id)
	scorebox = g.get_scores()
	away_scores = scorebox[0]
	home_scores = scorebox[1]
	away_R = g.away_R
	away_H = g.away_H
	away_E = g.away_E
	home_R = g.home_R
	home_H = g.home_H
	home_E = g.home_E

	home_bat = Batting.objects.filter(game = g).filter(team =g.home).order_by("sequence")
	home_pit = Pitching.objects.filter(game= g).filter(team =g.home).order_by("sequence")
	away_bat = Batting.objects.filter(game = g).filter(team =g.away).order_by("sequence")
	away_pit = Pitching.objects.filter(game= g).filter(team =g.away).order_by("sequence")

	for batter in away_bat:
		batter.calculate_AB()
	for batter in home_bat:
		batter.calculate_AB()

	for pitcher in away_pit:
		pitcher.calculate_IP()
		pitcher.convert_wl()
	for pitcher in home_pit:
		pitcher.calculate_IP()
		pitcher.convert_wl()

	context = {'game': g, 'away_scores': away_scores, 'home_scores': home_scores, 'home_bat' : home_bat, 'home_pit' : home_pit , 'away_bat' : away_bat , 'away_pit' : away_pit, 'away_R': away_R, 'away_H': away_H, 'away_E': away_E, 'home_R': home_R, 'home_H': home_H, 'home_E': home_E}


	return render (request , 'sbleague/game.html' , context)

@login_required(login_url='/admin')
def newgame(request):
	if request.method != 'POST':
		teams = Team.objects.all()
		context = {'teams':teams}
		return render (request , 'sbleague/newgame.html',context)

	else :

		teams = Team.objects.all()

		home_teamID = request.POST.get("hometeamID", "")
		away_teamID = request.POST.get("awayteamID", "")
		
		hometeam = Team.objects.get(pk=home_teamID)
		awayteam = Team.objects.get(pk=away_teamID)

		homeplayer = Member.objects.filter(team = home_teamID).order_by("number")
		awayplayer = Member.objects.filter(team = away_teamID).order_by("number")

		date = request.POST.get("date", "")
		location = request.POST.get("location", "")		
		game_id  = request.POST.get("game_id", "")



#############################################################################
		away_record = request.POST.get("away_rd", "")
		home_record = request.POST.get("home_rd", "")

		record = None
		record_err = ""
		# ===== record parser
		if( len(away_record) and len(home_record) ):
			awayteam_name = awayteam.name.encode('utf8')[0:6]
			hometeam_name = hometeam.name.encode('utf8')[0:6]
			away_table = text_to_table(away_record.encode('utf8'))
			home_table = text_to_table(home_record.encode('utf8'))
			record, record_err = parse_game_record(awayteam_name, None, away_table, hometeam_name, None, home_table)
			
			record.game_type    = "台大慢壘聯盟"
			record.date         = date
			record.location     = location
			record.game_id      = game_id
			record.away.raw_record = away_record.encode('utf8')
			record.home.raw_record = home_record.encode('utf8')
		else:
			if( len(away_record) == 0 ):
				record_err = "Away 沒有記錄"
			else:
				record_err = "Home 沒有記錄"

#############################################################################
		


		if( date == u'' ):
			err_message = "請輸入日期"
			context = {'teams': teams, 'awayteam': awayteam, 'hometeam': hometeam, 'date': date, 'location': location, 'game_id': game_id, 'away_record': away_record, 'home_record': home_record, 'warning': err_message}
			
			return render(request, 'sbleague/newgame.html', context)
		

		if( game_id == u'' ):
			err_message = "請輸入場次編號"
			context = {'teams': teams, 'awayteam': awayteam, 'hometeam': hometeam, 'date': date, 'location': location, 'game_id': game_id, 'away_record': away_record, 'home_record': home_record, 'warning': err_message}

			return render(request, 'sbleague/newgame.html', context)


		game_exist = True
		try:
			new = Game.objects.get(gameID=game_id)

		except Game.DoesNotExist: # --- add new game

			game_exist = False

			max_batter_nums  = 25
			max_pitcher_nums = 5

			if( record != None and record_err == ""): 
				# --- append batter_num to 25 and pitcher_num to 5
				if( record.away.nBatters < max_batter_nums ):
					for i in range(max_batter_nums-record.away.nBatters):
						record.away.batters.append(rdBatter())

				if( record.home.nBatters < max_batter_nums ):
					for i in range(max_batter_nums-record.home.nBatters):
						record.home.batters.append(rdBatter())

				if( record.away.nPitchers < max_pitcher_nums ):
					for i in range(max_pitcher_nums-record.away.nPitchers):
						record.away.pitchers.append(rdPitcher())

				if( record.home.nPitchers < max_pitcher_nums ):
					for i in range(max_pitcher_nums-record.home.nPitchers):
						record.home.pitchers.append(rdPitcher())

		if( game_exist ):
			err_message = "重複的場次編號"
			context = {'teams': teams, 'awayteam': awayteam, 'hometeam': hometeam, 'date': date, 'location': location, 'game_id': game_id, 'away_record': away_record, 'home_record': home_record, 'warning': err_message}
			
			return render(request, 'sbleague/newgame.html', context)


		# === record error
		if( record_err != "" ):	
			err_message = record_err
			context = {'teams': teams, 'awayteam': awayteam, 'hometeam': hometeam, 'date': date, 'location': location, 'game_id': game_id, 'away_record': away_record, 'home_record': home_record, 'warning': err_message}
			
			return render(request, 'sbleague/newgame.html', context)

		# === success add new game
		if 'send' in request.POST: # --- send data
			context = {'hometeam': hometeam, 'awayteam': awayteam, 'homeplayer': homeplayer ,'awayplayer': awayplayer, 'date': date, 'location': location , 'game_id': game_id, 'home_away': range(2), 'max_batter_nums': max_batter_nums, 'max_pitcher_nums': max_pitcher_nums, 'record': record}

			return render(request, 'sbleague/newgame_detail.html', context)

		elif 'download' in request.POST:

			filename = '%d.txt' %int(game_id)
			filepath = 'sbleague/static/txt/%s' %filename
			with open(filepath, 'w') as f:
				f.write(record.post_ptt)
				print "save %s" %filepath

			response = HttpResponse(FileWrapper( file(filepath) ), content_type=mimetypes.guess_type(filepath)[0] )
			response['Content-Disposition'] = 'attachment; filename=%s' %filename
			response['Content-Length'] = os.path.getsize(filepath)
			
			return response

		else: # --- preview
			err_message = "preview"
			context = {'teams': teams, 'awayteam': awayteam, 'hometeam': hometeam, 'date': date, 'location': location, 'game_id': game_id, 'away_record': away_record, 'home_record': home_record, 'warning': err_message, 'record': record, 'preview': True}
			
			return render(request, 'sbleague/newgame.html', context)

def get_boxscore_from_web(request, awayid, homeid):
	away_score = ""
	for i in range(1, 8):
		name = "score_%s_%d" %(awayid, i)
		score = request.POST.get(name, "")
		away_score += score
		if(i < 7):
			away_score += ","
	
	home_score = ""
	for i in range(1, 8):
		name = "score_%s_%d" %(homeid, i)
		score = request.POST.get(name, "")
		home_score += score
		if(i < 7):
			home_score += ","
	
	box = away_score + ";" + home_score
	return box	

def addgame(request):
	game_id = request.POST.get("game_id","")
	awayid 	= request.POST.get("awayid","")
	homeid 	= request.POST.get("homeid","")
	box 	= get_boxscore_from_web(request, awayid, homeid)
	
	game = Game(gameID = game_id, date = request.POST.get("date","") ,location=request.POST.get("location","") , away=Team.objects.get(teamID = awayid) , home =Team.objects.get(teamID =homeid), scorebox =box, away_R = request.POST.get("away_R", ""), away_H = request.POST.get("away_H", ""), away_E = request.POST.get("away_E", ""), home_R = request.POST.get("home_R", ""), home_H = request.POST.get("home_H", ""), home_E = request.POST.get("home_E", "") )
	game.save()
	game = Game.objects.get(gameID = game_id)

	for team in [homeid,awayid] :
		
		for i in range(1,26):

			player = request.POST.get("id_"+team+"_"+str(i),"")
			player_id = int(player)
			if player_id != 0:
				Pa=int(request.POST.get("pa_"+team+"_"+str(i),""))
				Single=int(request.POST.get("single_"+team+"_"+str(i),""))
				Double=int(request.POST.get("double_"+team+"_"+str(i),""))
				Triple=int(request.POST.get("triple_"+team+"_"+str(i),""))				
				Hr=int(request.POST.get("hr_"+team+"_"+str(i),""))
				Bb=int(request.POST.get("bb_"+team+"_"+str(i),""))
				Rbi=int(request.POST.get("rbi_"+team+"_"+str(i),""))
				Run=int(request.POST.get("run_"+team+"_"+str(i),""))
				So=int(request.POST.get("so_"+team+"_"+str(i),""))
				Sf=int(request.POST.get("sf_"+team+"_"+str(i),""))
				myteam = int(team)

				batting = Batting(game = game , member=Member.objects.get(memberID = player_id) , team = Team.objects.get(teamID = myteam) , sequence = i , pa = Pa,single = Single , double = Double , triple = Triple , hr= Hr , rbi = Rbi ,run=Run ,bb=Bb,so=So,sf=Sf)
				batting.save()

		for i in range(1,6):
			pitcher = request.POST.get("pid_"+team+"_"+str(i),"")
			pid = int(pitcher)
			if pid != 0:
				outs = int (request.POST.get("outs_"+team+"_"+str(i),""))
				pa = int (request.POST.get("ppa_"+team+"_"+str(i),""))
				h = int (request.POST.get("ph_"+team+"_"+str(i),""))
				bb = int (request.POST.get("pbb_"+team+"_"+str(i),""))
				hr = int (request.POST.get("phr_"+team+"_"+str(i),""))
				so = int (request.POST.get("pso_"+team+"_"+str(i),""))
				r = int (request.POST.get("pr_"+team+"_"+str(i),""))
				er = int (request.POST.get("per_"+team+"_"+str(i),""))
				fo = int (request.POST.get("pfo_"+team+"_"+str(i),""))
				go = int (request.POST.get("pgo_"+team+"_"+str(i),""))
				wl = request.POST.get("wl_"+team+"_"+str(i))
				if wl== 'win':
					win=1
					lose=0
				elif wl =='lose' :
					win=0
					lose=1
				else :
					win=0
					lose=0
				myteam = int(team)

				pitching = Pitching(game=game , member = Member.objects.get(memberID=pid),team=Team.objects.get(teamID=myteam),sequence=i,outs=outs,pa=pa,h=h,hr=hr,bb=bb,so=so,r=r,er=er,fo=fo,go=go,win=win,lose=lose)
				pitching.save()

	return redirect("/game/"+str(game.gameID))
	

def login(request):
	if request.method != 'POST' :
		return redirect("/")
	else :
		name = request.POST.get("id")
		password = request.POST.get("password")

		user = authenticate(username = name , password = password)
		if user is not None:
			if user.is_active:
				log_account(request,user)
				return index(request)

		else:
			return redirect("/")

def logout(request):
	out_account(request)
	return index(request)

def mod(request,game_id):
	if request.method !='POST' :
		return redirect("/")
	else :
		game = Game.objects.get(gameID = game_id)
		button=request.POST.get("button","")
		if button == "header" :
			game.location=request.POST.get("location","")
			game.date=request.POST.get("date","")
			game.save()
		elif button == "gamebox" : 
			away=request.POST.get("away","")
			home=request.POST.get("home","")
			game.scorebox=get_boxscore_from_web(request,away,home)
			game.away_R = request.POST.get("away_R","")
			game.away_H = request.POST.get("away_H","")
			game.away_E = request.POST.get("away_E","")
			game.home_R = request.POST.get("home_R","")
			game.home_H = request.POST.get("home_H","")
			game.home_E = request.POST.get("home_E","")
			game.save()
#		elif button == "mod_bat" :

		elif button == "del_bat" :
			team = request.POST.get("team","")
			sequence = request.POST.get("sequence","")

			bat_rec = Batting.objects.filter(Q(game=game) , Q(team=team) , Q(sequence = sequence))
			bat_rec[0].delete()


		return redirect("/game/"+str(game_id))

@login_required(login_url='/admin')
def register(request):
	if request.method != 'POST' :  #第一次進來
		teams = Team.objects.filter(current__gte = 1)
		context={'teams':teams,'thirty':range(30)}
		return render(request,"sbleague/register.html",context)

	else :
		team_n = request.POST.get("team","")
		team = Team.objects.get(teamID=int(team_n))
		for i in range(1,31) : 
			name = request.POST.get("name_"+str(i),"")
			number = request.POST.get("number_"+str(i),"")
			stu_id = request.POST.get("id_"+str(i),"") 
			old_id = request.POST.get("old_id"+str(i),"")

			if len(name)>0:
				try:
					player=Member.objects.get(studentID = stu_id)
				except ObjectDoesNotExist:
					#找不到，先看看是不換學號
					try:
						player = Member.objects.get(studentID = old_id)
					except ObjectDoesNotExist:
						#又找不到，是新的人
						member = Member(name=name,number=number,studentID=stu_id,current=1,team=team)
						member.save()

						continue
						
					player.studentID = stu_id
					player.team = team

				#找到了
				player.save()
				
			else:
				break

		teams = Team.objects.order_by("current")
		context={'teams':teams,'thirty':range(1,31),'alert':team.name}
		return render(request,"sbleague/register.html",context)


# def showplayers(request):
#     players = Member.objects.all()
#     context = {'players':players}
#     return render(request, "sbleague/showplayers.html", context)