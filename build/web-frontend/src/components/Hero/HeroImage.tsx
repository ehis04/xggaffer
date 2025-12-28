import "./css/HeroImage.css";
import HeroImg from "../../images/general/HeroImage.jpeg";

export const HeroImage = () => {
  return (
    <div className="heroCard">
      <div className="heroCard-overlay">
      </div>
      <div className="heroImage">
        <img src={HeroImg} alt="hero" className="heroImg" />
      </div>
    </div>
  );
};
