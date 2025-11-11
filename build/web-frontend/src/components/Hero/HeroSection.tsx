import { GetStartedButton } from "../Buttons/GetStartedButton";
import { HeroImage } from "./HeroImage";
import { PrimaryHeader } from "./PrimaryHeader";
import { SecondaryHeader } from "./SecondaryHeader";
import "./css/HeroSection.css";

export const HeroSection = () => {
  return (
    <div className="heroSection">
      <div className="heroSectionLeft">
        <PrimaryHeader />
        <SecondaryHeader />
        <GetStartedButton />
      </div>
      <div className="heroSectionRight">
        <HeroImage/>
      </div>
    </div>
  );
};
