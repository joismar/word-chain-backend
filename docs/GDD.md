# Word Chain - GDD

## 📒 Overview
### Introdução
Word Chain é um game com uma jogabilidade simples e divertida, no estilo [Gartic.IO](https://gartic.io/), onde os jogadores vão disputar online a sua capacidade de fazer correntes de palavras, o mais rápido possível, sem repetir. 

Uma corrente de palavra segue o seguinte exemplo: se eu falar "verruga", você deve falar qualquer palavra que começe com qualquer conjunto de palavras do fim da minha, como por exemplo "garagem". A pontuação é dada pela quantidade de palavras que o jogador conseguir juntar com a anterior.

## 🛠️ Gameplay e mecanicas
### Gameplay
#### 1. Inicio do jogo
- Inicialmente, o jogo escolherá aleatoriamente para votação algumas palavras equivalente a quantidade de jogadores;
- A palavra escolhida pela maioria será a paravra inicial, caso haja empate o jogo exibirá uma mensagem extrovertida de aviso e repete o sorteio;
- Terá um tempo para escolher, caso esse tempo limite seja atingido o jogo sortea automaticamente uma palavra ou, se já tiver votação a regra do tópico acima será avaliada;
- Após isso, o jogo começa selecionando aleatoriamente um jogador para começar, esse jogador terá um tempo (5 segundos, por exemplo) para escrever a palavra que vir a cabeça, o jogo checa se essa palavra existe no dicionário da lingua, se existir, calcula a pontuação e passa pra o próximo.

#### 2. Decorrer da partida
Os próximos jogadores deverão digitar qualquer palavra que exista na lingua, que tenha mais de duas letras e que faça match com o fim da palavra anterior, caso a palavra que ele digitar não faça match, ele pode tentar até o tempo acabar, caso positivo ele ganha uma [pontuação](#pontuação-e-multiplicador-de-pontos) referente a quantidade de letras que conseguiu juntar + um [multiplicador](#pontuação-e-multiplicador-de-pontos) de pontos de acordo com o tempo. As regras da partida estão especificadas em [regras](#regras).

#### 3. Fechamento de corrente
Em determinado momento, pode haver um fechamento de corrente, quando o fim da ultima palavra fecha com a primeira digitada. Nesse caso o jogador ganha um bônus de acordo com o tamanho da corrente e a quantidade de letras conectadas, e a corrente reinicia. Os detalhes dessa mecanica será explicado em [fechamento de corrente](#fechamento-de-corrente).

#### 4. Fim de jogo
O jogo termina se a alguma de fim de jogo especificado no [modo de jogo](#modos-de-jogo) escolhido for satisfeita.

### Mecanicas
#### Regras
- Todos os jogadores ganham [multiplicador](#pontuação-e-multiplicador-de-pontos) de ponto de acordo com a velocidade em que responderam;
- A palavra digitada deve ter mais de duas letras;
- A pontuação é exatamente a quantidade de letras que conseguiu combinar, por exemplo: a palavra era "dado", o jogador digitou "doente", ele fez 2pts + o [multiplicador](#pontuação-e-multiplicador-de-pontos) de tempo;
- As pontuações e caracteres especiais como "ç" serão convertidos, ou seja "maca" e "maçã" são a mesma coisa.
- Será utilizado um dicionário de palavras no idioma da partida, onde será verificado se as palavras existem, poderá haver votação após o termino da rodada se a palavra digitada existe ou não para inserir ou remover das próximas partidas.

#### Pontuação e multiplicador de pontos
- Os jogadores ganharão pontos equivalente a quantidade de letras que serão combinadas, esses pontos serão multiplicados com o tempo restante, por exemplo, o jogador ganhou 2 pontos e terminou quando faltava 3 minutos pra terminar sua vez, logo ele recebeu 6 pontos.
- Caso a palavra digitada, combine com a palavra anterior, mas fique dentro dela (por exemplo "cabeca" -> "beca"), o jogador ganhará só metade do total de pontos.

#### Modos de jogo e configurações extras
- Pontuação: É definida uma pontuação máxima a ser atingida, o primeiro que atingir, vence a partida;
- Tempo: Um tempo limite é definido, quando tempo acaba, o jogar com mais pontos vence;
- Eliminação: Se um jogador repetir uma palavra, ele é eliminado, o ultimo jogador que sobrar ganha a partida;
- Penalidade de repetição: Se essa configuração estiver ativa, o jogador que repetir uma palavra, será penalizado e perderá pontos (a definir).

#### Fechamento de corrente
No fechamento de corrente, o fim da palavra atual tem que se conectar com o começo da de qualquer palavra digitada antes, por exemplo: em algum lugar da corrente existe a palavra "macarrão", depois de duas rodadas um jogador digitou "fumaça", ele fecha a corrente e acontece o seguinte:
- O jogador ganha uma pontuação bonus de acordo com o tamanho da corrente e a quantidade de letras que ele juntou;
- Todas as palavras do fechamento são colapsadas e destruídas, inclusive a ultima palavra digitada, a ultima palávra passa a ser a primeira antes do fechamento.

#### Embaralhamento da corrente
- Aleatoriamente o sistema irá embaralhar a corrente, mudando o layout da corrente, mas mantendo todas as regras de maching;

## 🌆 UI
- Mobile first: O MVP será um PWA;
- Tela principal: A tela incial, Lobby e tela de jogo serão as mesmas. O sistema irá interagir com o Player pelo Chat;
- - Placar/Lobby: essa tela terá os jogadores que forem entrando ou o placar da partida
- - Chat: O chat exibirá tudo que o usuário digita, e o Sistema irá interagir com o usuário perguntando nome, configuração da partida e iniciando o jogo, ele responderá com o código da partida que poderá ser passado para outros jogadores entrarem. Além disso, no decorrer da partida o chat informará as palavras digitadas e os usuários poderam conversar;
- - Corrente: A corrente exibirá todas as palavras da corrente, em ordem; todas as alterações de estado da corrente também serão mostradas nesse painel.