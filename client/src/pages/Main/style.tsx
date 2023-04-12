import styled from "styled-components";

export const Main = styled.main`
    background-color: rgba(255, 255, 255, 0.5);
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
`

export const Container = styled.div`
    background-color: #fff;
    width: 100%;
    max-width: 800px;
    padding: 0px 100px;
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
`

export const ChatContainer = styled.div`
    background-color: rgba(0, 0, 0, 0.5);
    border-radius: 3px;
    display: flex;
    flex-direction: column;
    width: 100%;
    padding: 20px;
    height: 100%;
    margin-bottom: 50px;
`
export const ChatBox = styled.div`
    border: 1px solid;
    height: 100%;
    margin-bottom: 20px;
`

export const ChatFooter = styled.div`
    width: 100%;
    height: 50px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 5px;
`