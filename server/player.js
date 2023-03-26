class Player {
  constructor (
    id=0, 
    name=null, 
    isHost=null, 
    score=0
  ) {
    this.score = score
  }

  giveScore(s) {
    this.score += s
  }
}

module.exports = Player