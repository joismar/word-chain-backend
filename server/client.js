const { io } = require("socket.io-client");
const socket = io("http://localhost:6666");
const gameModeSwitch = { 1:'local', 2:'online', 3:'host' }

function startClient(gameMode) {
  socket.on("connect", () => {
    console.log('Conectado!')
    socket.emit('gamemode', { gameMode: gameModeSwitch[parseInt(gameMode)] })
  });
  
  socket.on('waiting_players_local', () => {
    const players = prompt('Digite o nome dos jogadores separados por vírgula:')
    socket.emit('players', { players: players.split(',').map((player => player.trim())) })
  })
  
  socket.on('waiting_players_online', (data) => {
    if (!data) return
    if (!data.gameRoom) return
  
    console.log(`Sala ${data.gameRoom} criada!`)
    console.log('Aguardando jogadores...')
  })

  socket.on('player_joined', (name) => {
    console.log(`Jogador ${name} entrou na sessão.`)
  })
}

module.exports = startClient