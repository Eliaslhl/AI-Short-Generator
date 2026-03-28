#!/bin/bash
# create_test_users.sh
# Crée tous les comptes de test pour Youtube, Twitch et Combo avec les bons plans et quotas

API_URL="http://localhost:8000"
PASSWORD="Test1234!"
HEADER="Content-Type: application/json"

# Youtube Platform
curl -s -X POST "$API_URL/auth/register" -H "$HEADER" -d '{"email":"test.youtube.free@test.com","password":"'$PASSWORD'","full_name":"YouTube Free"}'

curl -s -X POST "$API_URL/auth/register" -H "$HEADER" -d '{"email":"test.youtube.standard@test.com","password":"'$PASSWORD'","full_name":"YouTube Standard"}'

curl -s -X POST "$API_URL/auth/register" -H "$HEADER" -d '{"email":"test.youtube.pro@test.com","password":"'$PASSWORD'","full_name":"YouTube Pro"}'

curl -s -X POST "$API_URL/auth/register" -H "$HEADER" -d '{"email":"test.youtube.proplus@test.com","password":"'$PASSWORD'","full_name":"YouTube ProPlus"}'

# Twitch Platform
curl -s -X POST "$API_URL/auth/register" -H "$HEADER" -d '{"email":"test.twitch.free@test.com","password":"'$PASSWORD'","full_name":"Twitch Free"}'

curl -s -X POST "$API_URL/auth/register" -H "$HEADER" -d '{"email":"test.twitch.standard@test.com","password":"'$PASSWORD'","full_name":"Twitch Standard"}'

curl -s -X POST "$API_URL/auth/register" -H "$HEADER" -d '{"email":"test.twitch.pro@test.com","password":"'$PASSWORD'","full_name":"Twitch Pro"}'

curl -s -X POST "$API_URL/auth/register" -H "$HEADER" -d '{"email":"test.twitch.proplus@test.com","password":"'$PASSWORD'","full_name":"Twitch ProPlus"}'

# Combo Platform
curl -s -X POST "$API_URL/auth/register" -H "$HEADER" -d '{"email":"test.combo.standard@test.com","password":"'$PASSWORD'","full_name":"Combo Standard"}'

curl -s -X POST "$API_URL/auth/register" -H "$HEADER" -d '{"email":"test.combo.pro@test.com","password":"'$PASSWORD'","full_name":"Combo Pro"}'

curl -s -X POST "$API_URL/auth/register" -H "$HEADER" -d '{"email":"test.combo.proplus@test.com","password":"'$PASSWORD'","full_name":"Combo ProPlus"}'

echo "Comptes de test créés. Pense à ajuster les plans/quotas manuellement si besoin."
