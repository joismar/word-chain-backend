class Game {
  players = []
  turnIndex = 0

  turnPlayer() {
    return this.players[this.turnIndex]
  }

  swapTurn() {
    if (this.players.length-1 === this.turnIndex) {
      this.turnIndex = 0
      return
    }
        
    this.turnIndex += 1
  }
}

module.exports = Game