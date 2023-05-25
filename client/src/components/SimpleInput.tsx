import styled from 'styled-components';
import React from 'react';

const SimpleInput = ({nameExample}: {nameExample: string}) => {
    return (
        <Container>
            <Input type="text" placeholder={nameExample}/>
        </Container>
    );
}

const Container = styled.div`
  /* border: yellow solid 1px; */
`
const Input = styled.input`
    background-color:  rgba(255, 255, 255, 0.5);
    height: 35px;
    border-radius: 3px;
    outline: none;
    border: none;
    /* border-radius: 3px; */
`

export default SimpleInput;

