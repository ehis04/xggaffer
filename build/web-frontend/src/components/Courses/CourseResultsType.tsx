export const CourseResultsType = ({type, cType, doneCount, items}) => {
    return (
        <div key={type} className="crt-row">
            <div className="crt-left">
                <div className="crt-name" style={{background: cType.bg, color: cType.colour}}>
                    {cType.label} task
                </div>
            </div>
            <span className="crt-score">
                {doneCount}/{items.length}
            </span>
        </div>
    )
}