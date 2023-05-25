import React from 'react';
import styled from 'styled-components';
import SimpleInput from './SimpleInput';
import { Button } from './CustomButton/style';
import { useState } from 'react';

// import { Container } from './styles';



const Modal: React.FC = () => {
  const [modalOff, setModalOff] = useState(false);
  if (modalOff) {
    return null;
  } else {
    return(
      <Container>
        <ModalBox>
          <TitleGame>
            <h1>WORDCHAIN</h1>
          </TitleGame>
          <NameContainer>
            <h3>Insira seu nome:</h3>
            <NameBox>
              {/* Recuperar o nome e levar pro Main */}
              <SimpleInput nameExample={"Chupetinha da Silva"}/>
              <ButtonBox>
                <Button onClick={() => setModalOff(true)}>OK</Button>
              </ButtonBox>
            </NameBox>
          </NameContainer>
        </ModalBox>
      </Container>
      )
  }
  
}

export default Modal;

const Container = styled.div`
  
  background-color: rgba(0, 0, 0, 0.5);
  height: 100vh;
  width: 100vw;
  /* margin: 0 auto; */
  display: flex;
  position: absolute;
  align-items: center;
  justify-content: center;
  z-index: 999;
`;

const ModalBox = styled.div`
  background-color: rgba(255, 255, 255, 0.5);
  border: black solid 1px;
  border-radius: 3px;
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: space-around;
  height: 50vh;
  min-width: 350px;
`

const TitleGame = styled.div`
  /* text-align: center; */
`
const NameContainer = styled.div`
  /* width: 60%; */
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  /* width: 100vw; */
  /* padding-left: 50px; */
  
`
const NameBox = styled.div`
  width: 100%;
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
`
const ButtonBox = styled.div`
  /* border: red solid 1px; */
  margin-left: 50px;
  
`

