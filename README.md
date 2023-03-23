# Word Chain - GDD

## 📒 Overview
### Introdução
Word Chain é um game com uma jogabilidade simples e divertida, no estilo [Gartic.IO](https://gartic.io/), onde os jogadores vão disputar online a sua capacidade de fazer correntes de palavras, o mais rápido possível, sem repetir. 

Uma corrente de palavra segue o seguinte exemplo: se eu falar "verruga", você deve falar qualquer palavra que começe com qualquer conjunto de palavras do fim da minha, como por exemplo "garagem". A pontuação é dada pela quantidade de palavras que o jogador conseguir juntar com a anterior.

## 🛠️ Gameplay e mecanicas
### Gameplay
#### 1. Inicio do jogo
O jogo iniciará perguntando o nome de cada jogador. Após isso, o jogo começa selecionando aleatoriamente um jogador para começar, esse jogador terá um tempo (10 segundos, por exemplo) para escrever a palavra que vir a cabeça, o jogo checa se essa palavra existe no dicionário da lingua, se existir passa pra o próximo.

#### 2. Próximos jogadores
O próximo jogador deverá digitar qualquer palavra que exista na lingua, que tenha mais de duas letras e que faça match com o fim da palavra anterior, caso a palavra que ele digitar não faça match, ele pode tentar até o tempo acabar, caso positivo ele ganha uma pontuação referente a quantidade de letras que conseguiu juntar.

#### 3. Fechamento de corrente
Em determinado momento, pode haver um fechamento de corrente, quando o fim da ultima palavra fecha com a primeira digitada. Nesse caso o jogador ganha um bônus de acordo com o tamanho da corrente e a quantidade de letras conectadas, e a corrente reinicia. Os detalhes dessa mecanica será explicado no próximo tópico.

#### 4. Fim de jogo
O jogo pode terminar em duas condições: fim do tempo estabelecido ou pontuação máxima determinada.

### Mecanicas
#### Regras
- O primeiro jogador ganha a pontuação mínima, 1pt;
- Todos os jogadores ganham multiplicador de ponto de acordo com a velocidade em que responderam;
- A pontuação é exatamente a quantidade de letras que conseguiu dá match, por exemplo: a palavra era "dado", o jogador digitou "doente", ele fez 2pts + o multiplicador de tempo;
- As pontuações e caracteres especiais como "ç" serão convertidos, ou seja "maca" e "maçã" são a mesma coisa.
- É utilizado um dicionário de palavras no idioma da partida, onde será verificado se as palavras existem, poderá haver votação após o termino da rodada se a palavra digitada existe ou não para inserir ou remover das próximas partidas.

#### Fechamento de corrente
No fechamento de corrente, o fim da palavra atual tem que se conectar com o começo da primeira palavra digitada, por exemplo: a primeira palavra era "macarrão", depois de duas rodadas um jogador digitou "fumaça", ele fecha a corrente e acontece o seguinte:
- O jogador ganha uma pontuação de acordo com o tamanho da corrente e a quantidade de letras que ele juntou;
- A corrente colapsa e é reiniciada, ou seja, a primeira palavra agora é a próxima.

#### Fim de jogo
O jogo termina quando a pontuação máxima estabelecida é atingida ou quando o tempo estabelecido termina, ganha o jogador que fizer mais pontos.

## 🌆 Assets
