const httpServer = require("http").createServer();
const io = require("socket.io")(httpServer);
const fs = require('fs');

const Game = require('./game');
const Player = require('./player');

const words = fs.readFileSync('wordlist.txt', 'utf-8').toString().split('\n')
const gameSessions = {}

io.on('connection', (socket) => {
  console.log(`${socket.id} is connected.`);

  socket.on('gamemode', (data) => {
    switch (data.gameMode) {
      case 'local':
        socket.emit('waiting_players_local')
        break
      case 'host':
        const gameRoom = words[Math.floor(Math.random()*words.length)]
        socket.join(gameRoom)
        gameSessions[gameRoom] = new Game()
        gameSessions[gameRoom].players.push(new Player(socket.id, data.name, true))
        socket.emit('waiting_players_online', { gameRoom: gameRoom })
        break
      case 'online':
        if (!data) return
        if (!data.gameRoom) return
        if (!data.name) return
        gameSessions[data.gameRoom].players.push(new Player(socket.id, data.name))
        socket.emit('player_joined', data.name)
        break
    }
  })

  socket.on('start_game', (gamedata) => {

  })

  socket.on('game_data', (data) => {
    
  })

  socket.on('players', (data) => {
    for (const player in data.players)
      gameSessions[socket.id].players.push(new Player(socket.id, player.name))
    socket.emit('start_game')
  })
})

const PORT = 6666

httpServer.listen(PORT, () =>
  console.log(`Server listening at http://127.0.0.1:${PORT}`)
);