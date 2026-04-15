import type { ReactNode } from "react";
import "./css/LoginButton.css";
import Popup from "reactjs-popup";

interface LoginButtonProps {
  text: string;
  popup?: boolean;
  popupContent?: ReactNode;
  colour?: string;
  onClick?: () => void;
}

export const LoginButton = ({
  text,
  popup,
  popupContent,
  colour,
  onClick,
}: LoginButtonProps) => {
  const defaultColour = {
    base: "#83c5ada2",
    hover: "#83c5ad",
  };

  const baseColour = colour || defaultColour.base;

  const buttonText = text;

  const buttonComp = (
    <button
      className="loginButton"
      style={{ backgroundColor: baseColour, borderColor: baseColour }}
      onClick={onClick}
    >
      <div className="body">
        <p> {buttonText} </p>
      </div>
    </button>
  );

  if (popup && popupContent) {
    return (
      <Popup position="center center" modal trigger={buttonComp}>
        <div>{popupContent}</div>
      </Popup>
    );
  }

  return buttonComp;
};
