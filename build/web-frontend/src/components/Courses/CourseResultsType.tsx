export const CourseResultsType = ({type, cType, doneCount, items}) => {
    return (
        <div key={type} className="crt-row">
            <div className="crt-left">
                <div className="crt-icon" style={{background: cType.bg, color: cType.colour}}>
                    🎯
                </div>
                <span className="crt-name">{cType.label}</span>
            </div>
            <span className="crt-score">
                {doneCount}/{items.length}
            </span>
        </div>
    )
}