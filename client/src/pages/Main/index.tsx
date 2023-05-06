import React from 'react';
// import './style.css';
import { ChatContainer, Container, Main, ChatFooter, ChatBox } from './style';
import TitleBox from '../../components/Title';
import CustomButton from '../../components/CustomButton';
import Modal from '../../components/Modal';

function App() {
  return (
    <>
    <Modal/>
    <Main>
      <Container>
        <TitleBox title={"INICIO"}/>
        <ChatContainer>
          <ChatBox>
          </ChatBox>
          <ChatFooter>
            <CustomButton>entrar</CustomButton>
            <CustomButton>criar</CustomButton>
          </ChatFooter>
        </ChatContainer>
      </Container>
    </Main>
    </>
    
  );
}

export default App;

