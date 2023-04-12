import React from 'react';
import './style.css';
import { ChatContainer, Container, Main, ChatFooter, ChatBox } from './style';
import TitleBox from '../../components/Title';
import CustomButton from '../../components/CustomButton';

function App() {
  return (
    <Main>
      <Container>
        <TitleBox title={"INICIO"}/>
        <ChatContainer>
          <ChatBox>

          </ChatBox>
          <ChatFooter>
            <CustomButton>foda-se</CustomButton>
            <CustomButton>picles</CustomButton>
          </ChatFooter>
        </ChatContainer>
      </Container>
    </Main>
  );
}

export default App;

