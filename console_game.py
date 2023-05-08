import os

class Player:
  def __init__(self, id, name, score=0):
    self.id = id
    self.name = name
    self.score = score

  def giveScore(self, s):
    self.score += s

class Game:
  players = []
  turnIndex = 0
  session = None

  def __init__(self, session) -> None:
    self.session = session

  def turnPlayer(self):
    return self.players[self.turnIndex]

  def swapTurn(self):
    if self.turnIndex == len(self.players) - 1:
      self.turnIndex = 0
    else:
      self.turnIndex += 1

print('Carregando lista de palavras...')
with open('wordlist.txt', 'r', encoding='utf-8') as f:
    words = f.read().split('\n')

inGameWordList = []
game = Game('new_session')
game.players = []

playersNum = int(input('Quantos jogadores vão jogar? '))
for index in range(playersNum):
    player1Name = input(f'Qual nome do jogador {index+1}: ')
    player = Player()
    player.name = player1Name
    game.players.append(player)

def calculateScore(word, lastGameWord, inGameWord, inverse = False):
    scored = False
    for scoreLevel in [7,6,5,4,3,2,1]:
        if len(lastGameWord) < scoreLevel or len(word) < scoreLevel:
            continue

        userSlicedWord = word[-scoreLevel:] if inverse else word[:scoreLevel]
        lastGameSlicedWord = inGameWord[:scoreLevel] if inverse else inGameWord[-scoreLevel:]

        if userSlicedWord == lastGameSlicedWord:
            scored = True
            return scoreLevel

    if not scored:
        return 0

result = ''
firstChainWord = None
while True:
    os.system('cls' if os.name == 'nt' else 'clear')
    print(result)
    result = ''

    lastGameWord = inGameWordList[-1] if inGameWordList else None
    if lastGameWord:
        print('ULTIMA PALAVRA: ' + lastGameWord)

    print(' | '.join([f'{player.name}: {player.score}' for player in game.players]))

    word = input(f'[{game.turnPlayer().name}] Digite uma palavra: ')

    if word == 'Q':
        break

    if word not in words:
        result = 'Palavra não existe ou não é uma palavra brasileira ¬¬'
        continue

    if not inGameWordList:
        inGameWordList.append(word)
        firstChainWord = word
        game.swapTurn()
        continue

    if word in inGameWordList:
        result = 'Se lascou, essa palavra já foi chamada!'
        game.swapTurn()
        continue

    closedChainPoints = calculateScore(word, lastGameWord, firstChainWord, True)
    score = calculateScore(word, lastGameWord, inGameWordList[-1])

    if (closedChainPoints > 0) and (score > 0):
        result = f'PARABÉEENS, VOCÊ FECHOU UMA CORRENTE DE PALAVRAS DE {closedChainPoints} PONTO{"S" if closedChainPoints > 1 else ""}!\nE GANHOU MAIS {score} PONTO{"S" if score > 1 else ""}!\nJOGA DE NOVO!\n(corrente zerada)'
        inGameWordList.append(word)
        firstChainWord = word
        game.turnPlayer().giveScore(closedChainPoints + score)
        game.swapTurn()
        continue

    if score > 0:
        inGameWordList.append(word)
        game.turnPlayer().giveScore(closedChainPoints + score)
        game.swapTurn()
        result = f'Ganhou {score} pontos!'

