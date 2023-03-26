const prompt = require('prompt-sync')();
const startOfflineGame = require("./offlineGame");
const startClient = require('./client')

const gameMode = prompt('Qual modo de jogo você vai jogar?\n1 - Local\n2 - Online\n3 - Host\n')

if (parseInt(gameMode) === 1)
  startOfflineGame()

if (parseInt(gameMode) !== 1)
  startClient(gameMode)
  
