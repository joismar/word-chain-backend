import React from 'react';
import { Button } from './style';

const CustomButton = ({children}: {children: React.ReactNode}) => {
  return (
    <Button onClick={() => console.log("meu cu")}>{children}</Button>
    );
}

export default CustomButton;

