import React from 'react';
import styled from 'styled-components';


const TitleBox = ({title}: {title: string}) => {
  return (
    <Bar>
        <TextDiv>
            <Text>{title}</Text>
        </TextDiv>
    </Bar>
    );
}

const Bar = styled.div`
 
    background-color: rgba(0, 0, 0, 0.5);
    border-radius: 3px;
    width: 100%;
    height: 38px;
    padding: 20px;
    margin-bottom: 20px;
    margin-top: 50px;

`

const TextDiv = styled.div`
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    color: #fff;
`
const Text = styled.p`
    font-size: 26px;
    margin: 0;
    align-self: center;
`
export default TitleBox;