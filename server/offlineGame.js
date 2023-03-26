const fs = require('fs');
const Game = require('./game');
const Player = require('./player');
const prompt = require('prompt-sync')();

function startOfflineGame() {
  console.log('Carregando lista de palavras...')
  const words = fs.readFileSync('wordlist.txt', 'utf-8').toString().split('\n')
  process.stdout.write('\033c')

  const inGameWordList = []
  const game = new Game()
  game.players = []

  const playersNum = prompt('Quantos jogadores vão jogar? ')

  for (const index of Array(parseInt(playersNum)).keys()) {
    const player1Name = prompt(`Qual nome do jogador ${index+1}: `)
    const player = new Player()
    player.name = player1Name
    game.players.push(player)
  }

  const calculateScore = (word, lastGameWord, inGameWord, inverse = false) => {
    var scored = false
    for (const scoreLevel of [7,6,5,4,3,2,1]) {
      if (lastGameWord.length < scoreLevel || word.length < scoreLevel)
        continue

      const userSlicedWord = inverse ? word.slice(-scoreLevel) : word.slice(0, scoreLevel)
      const lastGameSlicedWord = inverse ? inGameWord.slice(0, scoreLevel) : inGameWord.slice(-scoreLevel)

      console.log(userSlicedWord, lastGameSlicedWord)
    
      if (userSlicedWord === lastGameSlicedWord) {
        scored = true
        return scoreLevel
      } 
    }

    if (!scored) 
      return 0
  }

  let result = ''
  let firstChainWord
  while (true) {
    process.stdout.write('\033c')
    console.log(result)
    result = ''

    const lastGameWord = inGameWordList.length > 0 ? inGameWordList.slice(-1)[0] : undefined
    if (lastGameWord) console.log('ULTIMA PALAVRA: ' + lastGameWord)

    console.log(game.players.map(player => 
      `${player.name}: ${player.score}`
    ).join(' | '))

    const word = prompt(`[${game.turnPlayer().name}] Digite uma palavra: `)

    if (word == 'Q') {
      break
    }

    if (!Boolean(words.includes(word))) {
      result = 'Palavra não existe ou não é uma palavra brasileira ¬¬'
      continue
    }

    if (inGameWordList.length === 0) {
      inGameWordList.push(word)
      firstChainWord = word
      game.swapTurn()
      continue
    }

    if (inGameWordList.includes(word)) {
      result = 'Se lascou, essa palavra já foi chamada!'
      game.swapTurn()
      continue
    }

    const closedChainPoints = calculateScore(word, lastGameWord, firstChainWord, true)
    const score = calculateScore(word, lastGameWord, inGameWordList.slice(-1)[0])

    if ((closedChainPoints > 0) && (score > 0)) {
      result = `PARABÉEENS, VOCÊ FECHOU UMA CORRENTE DE PALAVRAS DE ${closedChainPoints} PONTO${(closedChainPoints > 1) ? 'S' : ''}!\nE GANHOU MAIS ${score} PONTO${(score > 1) ? 'S' : ''}!\nJOGA DE NOVO!\n(corrente zerada)`
      inGameWordList.push(word)
      firstChainWord = word
      game.turnPlayer().giveScore(closedChainPoints + score)
      game.swapTurn()
      continue
    }

    if (score > 0) {
      inGameWordList.push(word)
      game.turnPlayer().giveScore(closedChainPoints + score)
      game.swapTurn()
      result = `Ganhou ${score} pontos!`
    }
  }
  
  return
}

module.exports = startOfflineGame